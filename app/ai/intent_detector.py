import json
from app.core.llm_client import get_chat_client, get_cheap_model

client     = get_chat_client()
CHEAP_MODEL = get_cheap_model()

INTENTS = ["create_order", "update_order", "cancel_order", "general_question", "confirm", "deny", "greeting"]

SYSTEM_PROMPT = """You are an intent classifier for an AI receptionist system.
Given a customer's message, classify it into exactly one intent from this list:
- create_order: customer wants to place a new order
- update_order: customer wants to change an existing order
- cancel_order: customer wants to cancel an order
- general_question: customer is asking about products, prices, availability
- confirm: customer is confirming something (yes, sure, okay, correct, go ahead)
- deny: customer is declining or saying no (no, cancel, stop, never mind)
- greeting: customer is greeting or just starting the conversation

Respond ONLY with a JSON object: {"intent": "<intent>", "confidence": <0.0-1.0>}"""


def detect_intent(transcript: str) -> dict:
    """Detect intent from a customer transcript using the cheap model."""
    try:
        response = client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": transcript}
            ],
            temperature=0,
            max_tokens=50
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        result["tokens_used"] = response.usage.total_tokens
        return result
    except Exception as e:
        print(f"Intent detection error: {e}")
        return {"intent": "general_question", "confidence": 0.5, "tokens_used": 0}
