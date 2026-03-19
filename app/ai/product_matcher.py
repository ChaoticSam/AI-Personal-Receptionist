"""
Product Matching Engine — maps natural language queries to catalog products.

Pipeline:
  1. Generate query embedding  (OpenAI text-embedding-3-small)
  2. Vector search             (pgvector cosine similarity, top-N candidates)
  3. LLM re-ranking            (gpt-4o-mini, only on top candidates)
  4. Availability check        (matched product may exist but be unavailable)
  5. Ambiguity detection       (ask customer to clarify if scores are too close)

Only runs when:
  - Intent is create_order / update_order
  - session.order_draft does NOT already have a confirmed product_id
"""

import json
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.config import OPENAI_API_KEY, EMBEDDING_MODEL
from app.core.llm_client import get_chat_client, get_embedding_client, get_cheap_model

# Chat client follows the active LLM_PROVIDER (openai or groq)
client           = get_chat_client()
# Embeddings are always OpenAI — Groq has no embeddings API
embedding_client = get_embedding_client()
CHEAP_MODEL      = get_cheap_model()

# Similarity threshold below which we consider a match too weak
CONFIDENCE_THRESHOLD = 0.70
# How many candidates to retrieve from vector search before LLM re-ranking
TOP_K = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_query_embedding(query: str) -> list[float]:
    response = embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=query)
    return response.data[0].embedding


def _vector_search(db: Session, business_id: str, query_vector: list[float], top_k: int = TOP_K) -> list[dict]:
    """
    Retrieve the top-K most similar products using pgvector cosine similarity.

    NOTE: No is_available filter here — we search all products so we can
    distinguish "product not in catalog" from "product exists but is unavailable".
    Availability is checked after matching so the AI can give the right message.
    """
    vec_str = "[" + ",".join(str(v) for v in query_vector) + "]"

    sql = text("""
        SELECT
            p.id           AS product_id,
            p.name         AS name,
            p.description  AS description,
            p.product_meta AS product_meta,
            p.is_available AS is_available,
            1 - (pe.embedding <=> :vec::vector) AS similarity
        FROM product_embeddings pe
        JOIN products p ON pe.product_id = p.id
        WHERE pe.business_id = :business_id
        ORDER BY pe.embedding <=> :vec::vector
        LIMIT :top_k
    """)

    rows = db.execute(sql, {"vec": vec_str, "business_id": str(business_id), "top_k": top_k}).fetchall()

    return [
        {
            "product_id": str(row.product_id),
            "name": row.name,
            "description": row.description or "",
            "is_available": row.is_available,
            "similarity": float(row.similarity),
        }
        for row in rows
    ]


def _llm_rerank(query: str, candidates: list[dict]) -> dict:
    """
    Ask gpt-4o-mini to pick the best match from the candidates.
    Returns {"product_id": str, "name": str, "confidence": float}
    """
    candidate_list = "\n".join(
        f"{i+1}. {c['name']} — {c['description']}" for i, c in enumerate(candidates)
    )

    prompt = f"""You are a product matching assistant.

Customer request: "{query}"

Available products:
{candidate_list}

Which product best matches the customer's request?
Respond ONLY with JSON: {{"index": <1-based index>, "confidence": <0.0-1.0>}}
If none match well, use index 0."""

    try:
        response = client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=50,
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        idx = result.get("index", 0)
        confidence = float(result.get("confidence", 0.0))
        tokens = response.usage.total_tokens

        if idx == 0 or idx > len(candidates):
            return {"product_id": None, "name": None, "is_available": None, "confidence": 0.0, "tokens_used": tokens}

        chosen = candidates[idx - 1]
        return {
            "product_id": chosen["product_id"],
            "name": chosen["name"],
            "is_available": chosen["is_available"],
            "confidence": confidence,
            "tokens_used": tokens,
        }
    except Exception as e:
        print(f"LLM re-ranking error: {e}")
        best = candidates[0]
        return {
            "product_id": best["product_id"],
            "name": best["name"],
            "is_available": best["is_available"],
            "confidence": best["similarity"],
            "tokens_used": 0,
        }


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class MatchResult:
    def __init__(
        self,
        product_id: str | None,
        product_name: str | None,
        confidence: float,
        is_ambiguous: bool,
        candidates: list[dict],
        is_available: bool = True,
        tokens_used: int = 0,
    ):
        self.product_id = product_id
        self.product_name = product_name
        self.confidence = confidence
        self.is_ambiguous = is_ambiguous
        self.candidates = candidates
        # False means the product was found in the catalog but is currently unavailable
        self.is_available = is_available
        self.tokens_used = tokens_used


def match_product(query: str, business_id: str, db: Session) -> MatchResult:
    """
    Full product matching pipeline.

    Returns a MatchResult with three distinct states:
      - product_id set + is_available=True   → confident match, proceed with order
      - product_id set + is_available=False  → found but unavailable, tell the customer
      - product_id=None + is_ambiguous=True  → ask customer to clarify
      - product_id=None + is_ambiguous=False → not in catalog at all
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
        # Embeddings always require OpenAI; bail out gracefully if key is missing
        return MatchResult(None, None, 0.0, False, [])

    total_tokens = 0

    try:
        # Step 1: embed the query
        query_vector = _get_query_embedding(query)

        # Step 2: vector search (all products, availability checked afterwards)
        candidates = _vector_search(db, business_id, query_vector, top_k=TOP_K)

        if not candidates:
            return MatchResult(None, None, 0.0, False, [], tokens_used=total_tokens)

        # Fast-path: clear winner with very high similarity — skip LLM re-rank
        top = candidates[0]
        if top["similarity"] >= 0.90 and len(candidates) > 1:
            second = candidates[1]
            gap = top["similarity"] - second["similarity"]
            if gap >= 0.20:
                return MatchResult(
                    product_id=top["product_id"],
                    product_name=top["name"],
                    confidence=top["similarity"],
                    is_ambiguous=False,
                    candidates=candidates,
                    is_available=(top["is_available"] == "true"),
                    tokens_used=0,
                )

        # Step 3: LLM re-rank on top candidates
        rerank = _llm_rerank(query, candidates)
        total_tokens += rerank.get("tokens_used", 0)
        confidence = rerank["confidence"]

        # Below threshold → ambiguous or not in catalog
        if confidence < CONFIDENCE_THRESHOLD or not rerank["product_id"]:
            # Ambiguous = multiple plausible candidates exist
            is_ambiguous = len(candidates) >= 2 and candidates[0]["similarity"] > 0.55
            return MatchResult(
                product_id=None,
                product_name=None,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                candidates=candidates[:2],
                tokens_used=total_tokens,
            )

        return MatchResult(
            product_id=rerank["product_id"],
            product_name=rerank["name"],
            confidence=confidence,
            is_ambiguous=False,
            candidates=candidates,
            is_available=(rerank["is_available"] == "true"),
            tokens_used=total_tokens,
        )

    except Exception as e:
        print(f"Product matching error: {e}")
        return MatchResult(None, None, 0.0, False, [], tokens_used=total_tokens)
