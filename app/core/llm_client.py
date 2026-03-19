"""
LLM Client Factory — single place to switch between AI providers.

Supported providers (set via LLM_PROVIDER env var):
  "openai"  (default) — GPT-4o-mini / GPT-4.1
  "groq"              — Llama 3.1 8B / Llama 3.3 70B

Both providers expose the OpenAI-compatible chat completions API, so the
calling code (intent_detector, llm_extractor, response_generator,
product_matcher) is identical regardless of which provider is active.

Embeddings are always OpenAI because Groq does not offer an embeddings API.

Usage
-----
    from app.core.llm_client import get_chat_client, get_embedding_client
    from app.core.llm_client import get_cheap_model, get_smart_model

    client = get_chat_client()
    model  = get_cheap_model()

    response = client.chat.completions.create(model=model, messages=[...])
"""

from app.config import (
    LLM_PROVIDER,
    OPENAI_API_KEY,
    CHEAP_MODEL,
    SMART_MODEL,
    GROQ_API_KEY,
    GROQ_CHEAP_MODEL,
    GROQ_SMART_MODEL,
)


def get_chat_client():
    """
    Return an OpenAI-compatible chat client for the active provider.
    Both OpenAI and Groq use the same .chat.completions.create() interface.
    """
    if LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env"
            )
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY)

    # Default: OpenAI
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


def get_embedding_client():
    """
    Always returns an OpenAI client for embeddings.
    Groq does not offer an embeddings API — embeddings are always OpenAI.
    """
    from openai import OpenAI
    return OpenAI(api_key=OPENAI_API_KEY)


def get_cheap_model() -> str:
    """
    Fast, cheap model for intent detection, slot extraction, product re-ranking.
    """
    if LLM_PROVIDER == "groq":
        return GROQ_CHEAP_MODEL
    return CHEAP_MODEL


def get_smart_model() -> str:
    """
    High-quality model for response generation and order confirmation.
    """
    if LLM_PROVIDER == "groq":
        return GROQ_SMART_MODEL
    return SMART_MODEL


def active_provider() -> str:
    """Human-readable summary of the active configuration."""
    return (
        f"Provider : {LLM_PROVIDER}\n"
        f"Cheap    : {get_cheap_model()}\n"
        f"Smart    : {get_smart_model()}\n"
        f"Embeddings: openai/{OPENAI_API_KEY[:8]}... (always)"
    )
