"""
Embedding Service — generates and upserts product vector embeddings.

Uses OpenAI text-embedding-3-small (1536 dims, cheap & fast).
Embeddings are built from a concatenated string of:
  product name + description + synonyms from metadata
"""

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import OPENAI_API_KEY, EMBEDDING_MODEL
from app.models.product import Product
from app.models.product_embedding import ProductEmbedding

client = OpenAI(api_key=OPENAI_API_KEY)


def build_embed_text(product: Product) -> str:
    """Construct the rich text string that will be embedded."""
    parts = [product.name]

    if product.description:
        parts.append(product.description)

    if product.product_meta:
        synonyms = product.product_meta.get("synonyms", [])
        parts.extend(synonyms)

    return " ".join(parts)


def generate_embedding(text: str) -> list[float]:
    """Call OpenAI embeddings API and return the vector."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def upsert_product_embedding(db: Session, product: Product) -> ProductEmbedding | None:
    """
    Generate an embedding for the product and upsert it into product_embeddings.
    Returns the saved ProductEmbedding, or None if OPENAI_API_KEY is not set.
    """
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-your"):
        print(f"Skipping embedding for product={product.id}: OPENAI_API_KEY not configured.")
        return None

    try:
        embed_text = build_embed_text(product)
        vector = generate_embedding(embed_text)

        # Upsert — update if exists, insert if not
        existing = db.query(ProductEmbedding).filter(
            ProductEmbedding.product_id == product.id
        ).first()

        if existing:
            existing.embedding = vector
            existing.embed_text = embed_text
            db.commit()
            db.refresh(existing)
            print(f"Embedding updated: product_id={product.id}")
            return existing
        else:
            record = ProductEmbedding(
                product_id=product.id,
                business_id=product.business_id,
                embedding=vector,
                embed_text=embed_text,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            print(f"Embedding created: product_id={product.id}")
            return record

    except Exception as e:
        print(f"Embedding generation failed for product={product.id}: {e}")
        db.rollback()
        return None
