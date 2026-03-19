"""
LLM Slot Extractor — fallback layer called only when rule-based extraction is insufficient.

Called when:
  - No slots were extracted by rules (ambiguous / complex input)
  - product_name is needed (always requires LLM — catalog context needed)
  - Multiple slots needed in one complex sentence

Uses gpt-4o-mini (cheap model) with temperature=0 for deterministic output.
"""

import json
from app.core.llm_client import get_chat_client, get_cheap_model

client      = get_chat_client()
CHEAP_MODEL = get_cheap_model()

_BASE_SYSTEM_PROMPT = """You are a slot extractor for an AI receptionist order system.
Given the conversation history and the current customer message, extract order-related information.

Extract ONLY what the customer has explicitly mentioned. Return null for anything not mentioned.

Always respond ONLY with a valid JSON object in this exact shape:
{
  "product_name": "<product name or null>",
  "quantity": <integer or null>,
  "deadline": "<ISO date YYYY-MM-DD or null>",
  "customer_notes": "<general notes or null>",
  "custom_fields": {},
  "missing": ["<list of slot names still needed>"]
}

Standard required slots: product_name, quantity
deadline and customer_notes are always optional.
Today's date for reference when parsing relative dates: {today}"""


def _build_llm_prompt(required_custom_fields: list[str], today: str) -> str:
    prompt = _BASE_SYSTEM_PROMPT.format(today=today)
    if required_custom_fields:
        fields_str = ", ".join(required_custom_fields)
        prompt += f"""

This product requires the following custom fields:
  Required custom fields: {fields_str}

Extract any of these that the customer mentions and put them inside "custom_fields".
Include any unfilled custom fields in the "missing" list."""
    return prompt


def llm_extract(
    customer_message: str,
    conversation_history: list,
    existing_draft: dict,
    required_custom_fields: list[str] | None = None,
) -> dict:
    """
    LLM-based slot extraction. Called as fallback by the hybrid slot filler.

    Returns dict with:
      product_name, quantity, deadline, customer_notes, custom_fields,
      missing, tokens_used, rule_extracted=False
    """
    from datetime import date
    required_custom_fields = required_custom_fields or []
    today = date.today().isoformat()

    history_text = "\n".join(
        f"{msg['role'].upper()}: {msg['message']}"
        for msg in conversation_history[-6:]
    )
    draft_display = {k: v for k, v in existing_draft.items() if not k.startswith("_")}
    context = (
        f"Conversation so far:\n{history_text}\n\n"
        f"Current order draft: {json.dumps(draft_display)}"
    )

    system_prompt = _build_llm_prompt(required_custom_fields, today)

    try:
        response = client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\nLatest customer message: {customer_message}"}
            ],
            temperature=0,
            max_tokens=250,
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)

        result.setdefault("product_name", None)
        result.setdefault("quantity", None)
        result.setdefault("deadline", None)
        result.setdefault("customer_notes", None)
        result.setdefault("custom_fields", {})
        result.setdefault("missing", [])
        result["tokens_used"] = response.usage.total_tokens
        result["rule_extracted"] = False
        return result

    except Exception as e:
        print(f"LLM extraction error: {e}")
        default_missing = ["product_name", "quantity"] + list(required_custom_fields)
        return {
            "product_name": None,
            "quantity": None,
            "deadline": None,
            "customer_notes": None,
            "custom_fields": {},
            "missing": default_missing,
            "tokens_used": 0,
            "rule_extracted": False,
        }
