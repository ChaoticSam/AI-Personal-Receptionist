"""
Response Generator — produces the final AI voice/text response using GPT-4o.

Two entry points:
  - generate_response()         → general responses for all conversation turns
  - generate_confirmation_prompt() → structured spoken order summary for customer confirmation
"""

from app.core.llm_client import get_chat_client, get_smart_model

client      = get_chat_client()
SMART_MODEL = get_smart_model()

SYSTEM_PROMPT = """You are a friendly and efficient AI receptionist for a business.
Your job is to help customers place orders, answer questions, and provide a smooth phone experience.

Guidelines:
- Keep responses concise — these will be spoken aloud (2–3 sentences max)
- Be warm but professional
- If asking for missing info, ask for ONE thing at a time
- Avoid filler phrases like "Certainly!" or "Of course!"
- Never mention that you are an AI unless directly asked
- If a product is unavailable, say so clearly and offer to help with something else
- If the customer's request is ambiguous, ask ONE clarifying question"""

CONFIRMATION_SYSTEM_PROMPT = """You are an AI receptionist reading back a customer's order summary over the phone.
Read the order details clearly and ask if everything is correct.
Keep it under 3 sentences. Be natural and conversational, not robotic."""


def generate_response(
    customer_message: str,
    conversation_history: list,
    intent: str,
    tool_result: dict | None = None,
    missing_slots: list | None = None,
    business_context: str = "",
) -> dict:
    """
    Generate the AI's next spoken response for all general turns.

    Returns:
        {"response": str, "tokens_used": int}
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if business_context:
        messages[0]["content"] += f"\n\nContext: {business_context}"

    for msg in conversation_history[-8:]:
        role = "user" if msg["role"] == "customer" else "assistant"
        messages.append({"role": role, "content": msg["message"]})

    context_parts = [f"Customer said: {customer_message}", f"Detected intent: {intent}"]

    if tool_result:
        context_parts.append(f"Tool result: {tool_result.get('message', '')}")
    if missing_slots:
        # Ask for ONE missing field at a time
        next_missing = missing_slots[0]
        context_parts.append(f"Ask the customer for: {next_missing}")

    messages.append({"role": "user", "content": "\n".join(context_parts)})

    try:
        response = client.chat.completions.create(
            model=SMART_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=120,
        )
        text = response.choices[0].message.content.strip()
        return {"response": text, "tokens_used": response.usage.total_tokens}
    except Exception as e:
        print(f"Response generation error: {e}")
        return {
            "response": "I'm sorry, I had trouble processing that. Could you please repeat?",
            "tokens_used": 0,
        }


def generate_confirmation_prompt(
    confirmation_summary: str,
    conversation_history: list,
) -> dict:
    """
    Generate the spoken order confirmation summary.
    Used specifically when draft_status transitions to 'ready_for_confirmation'.

    Returns:
        {"response": str, "tokens_used": int}
    """
    messages = [{"role": "system", "content": CONFIRMATION_SYSTEM_PROMPT}]

    for msg in conversation_history[-6:]:
        role = "user" if msg["role"] == "customer" else "assistant"
        messages.append({"role": role, "content": msg["message"]})

    messages.append({
        "role": "user",
        "content": f"Read back this order summary to the customer: {confirmation_summary}"
    })

    try:
        response = client.chat.completions.create(
            model=SMART_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=100,
        )
        text = response.choices[0].message.content.strip()
        return {"response": text, "tokens_used": response.usage.total_tokens}
    except Exception as e:
        print(f"Confirmation prompt generation error: {e}")
        return {"response": confirmation_summary, "tokens_used": 0}
