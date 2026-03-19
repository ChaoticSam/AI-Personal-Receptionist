"""
Conversation Engine — stateful AI pipeline orchestrator.

Pipeline per customer turn:
  1. Intent Detection         (cheap model, fast)
  2. Slot Filling             (cheap model; uses required_custom_fields from product_meta)
  3. Product Matching         (embedding + LLM re-rank; loads custom_fields requirements)
  4. OrderDraftEngine         (apply slots, advance draft_status, validate)
  5. Confirmation Gate        (never auto-confirm; always wait for explicit customer "yes")
  6. Tool Execution           (DB write only after confirmed)
  7. Response Generation      (smart model; uses confirmation summary when ready)
"""

from dataclasses import dataclass, field
from sqlalchemy.orm import Session

from app.core.session_manager import CallSession
from app.ai.intent_detector import detect_intent
from app.ai.slot_filler import extract_slots
from app.ai.product_matcher import match_product
from app.ai.order_draft_engine import order_draft_engine
from app.ai.tool_executor import execute_tool
from app.ai.response_generator import generate_response, generate_confirmation_prompt


# ---------------------------------------------------------------------------
# State machine constants
# ---------------------------------------------------------------------------

ORDER_INTENTS = {"create_order", "update_order"}
CONFIRM_INTENTS = {"confirm"}
DENY_INTENTS = {"deny", "cancel_order"}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ProcessResult:
    response: str
    intent: str
    intent_confidence: float
    current_state: str
    draft_status: str
    slots_collected: dict = field(default_factory=dict)
    missing_slots: list = field(default_factory=list)
    tool_executed: str | None = None
    tool_result: dict | None = None
    total_tokens_used: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_required_custom_fields(product_id: str, db: Session) -> list[str]:
    """Look up the product's required custom fields from product_meta."""
    if not product_id:
        return []
    try:
        from app.models.product import Product
        product = db.query(Product).filter(Product.id == product_id).first()
        if product and product.product_meta:
            return product.product_meta.get("custom_fields", [])
    except Exception as e:
        print(f"Could not load custom fields for product {product_id}: {e}")
    return []


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class ConversationEngine:

    def process(
        self,
        customer_message: str,
        session: CallSession,
        db: Session,
        business_context: str = "",
    ) -> ProcessResult:
        """Process a single customer turn and return a structured result."""

        total_tokens = 0
        tool_executed: str | None = None
        tool_result: dict | None = None
        missing_slots: list = []
        slots_collected: dict = {}

        # ── 1. Intent Detection ────────────────────────────────────────────
        intent_data = detect_intent(customer_message)
        intent = intent_data["intent"]
        confidence = intent_data.get("confidence", 1.0)
        total_tokens += intent_data.get("tokens_used", 0)

        session.add_message(role="customer", message=customer_message)

        current_state = session.state

        # ── 2. State: customer is confirming or denying ────────────────────
        if current_state == "awaiting_confirmation" and intent in CONFIRM_INTENTS:
            is_valid, missing = order_draft_engine.validate(session.order_draft)
            if is_valid:
                draft = session.order_draft
                tool_result = execute_tool(
                    "create_order",
                    session=session,
                    db=db,
                    product_id=draft.get("product_id"),
                    quantity=draft.get("quantity", 1),
                    order_notes=draft.get("customer_notes"),
                    custom_fields=draft.get("custom_fields", {}),
                )
                tool_executed = "create_order"
                draft["draft_status"] = "confirmed"
                session.state = "order_placed"
                current_state = "order_placed"
            else:
                # Somehow still missing fields — go back to collecting
                missing_slots = missing
                session.state = "collecting_order"
                current_state = "collecting_order"

        elif current_state in ("collecting_order", "awaiting_confirmation") and intent in DENY_INTENTS:
            order_draft_engine.reset(session)
            current_state = "idle"
            tool_result = {"success": False, "message": "No problem. I've cancelled that order. How can I help you?"}

        # ── 3. State: order intent (create / update) ───────────────────────
        elif intent in ORDER_INTENTS or current_state == "collecting_order":
            # Load required custom fields from the already-matched product (if known)
            required_custom_fields = session.order_draft.get("_required_custom_fields") or []

            # Context-aware slot: the slot the AI last asked the customer for
            # e.g. "quantity", "text", "image" — enables rule-based direct capture
            expected_slot = session.order_draft.get("_expected_slot")

            # ── Slot Filling ───────────────────────────────────────────────
            slot_data = extract_slots(
                customer_message,
                conversation_history=session.conversation_history,
                existing_draft=session.order_draft,
                required_custom_fields=required_custom_fields,
                expected_slot=expected_slot,
            )
            total_tokens += slot_data.get("tokens_used", 0)

            # Apply slots to draft
            updated = order_draft_engine.apply_slots(session.order_draft, slot_data)
            slots_collected = updated
            session.state = "collecting_order"
            current_state = "collecting_order"

            # ── Product Matching ───────────────────────────────────────────
            raw_product_name = session.order_draft.get("product_name")
            product_already_resolved = bool(session.order_draft.get("product_id"))

            if raw_product_name and not product_already_resolved:
                match = match_product(
                    query=raw_product_name,
                    business_id=session.business_id,
                    db=db,
                )
                total_tokens += match.tokens_used

                if match.is_ambiguous:
                    missing_slots = ["product_clarification"]
                    session.order_draft["_ambiguous_options"] = [c["name"] for c in match.candidates]

                elif match.product_id and not match.is_available:
                    session.order_draft.pop("product_name", None)
                    session.order_draft.pop("product_id", None)
                    session.order_draft["_unavailable_product"] = match.product_name
                    missing_slots = ["unavailable_product"]
                    session.state = "idle"
                    current_state = "idle"

                elif match.product_id:
                    session.update_order_draft({
                        "product_id": match.product_id,
                        "product_name": match.product_name,
                    })
                    slots_collected["product_id"] = match.product_id
                    slots_collected["product_name"] = match.product_name

                    # Load product-specific required custom fields
                    required_custom_fields = _load_required_custom_fields(match.product_id, db)
                    session.order_draft["_required_custom_fields"] = required_custom_fields

            # ── Advance draft status ───────────────────────────────────────
            if current_state != "idle":
                order_draft_engine.advance_status(session.order_draft)
                is_valid, missing = order_draft_engine.validate(session.order_draft)
                missing_slots = missing_slots or missing

                # Store the next slot to ask for — enables context-aware rule extraction
                # on the customer's next turn (skips LLM when answer is simple)
                if missing_slots:
                    session.order_draft["_expected_slot"] = missing_slots[0]
                else:
                    session.order_draft.pop("_expected_slot", None)

                if is_valid and not missing_slots:
                    # All required info collected — move to confirmation gate
                    session.order_draft["draft_status"] = "ready_for_confirmation"
                    session.state = "awaiting_confirmation"
                    current_state = "awaiting_confirmation"

        # ── 4. Cancel intent (outside of order flow) ──────────────────────
        elif intent == "cancel_order":
            confirmed_order_id = session.order_draft.get("_confirmed_order_id")
            if confirmed_order_id:
                tool_result = execute_tool("cancel_order", session=session, db=db, order_id=confirmed_order_id)
                tool_executed = "cancel_order"
                order_draft_engine.reset(session)
            else:
                tool_result = {"success": False, "message": "There is no active order to cancel right now."}
            current_state = "idle"

        else:
            session.state = "idle"
            current_state = "idle"

        # ── 5. Build response context ──────────────────────────────────────
        ambiguous_options = session.order_draft.get("_ambiguous_options")
        unavailable_product = session.order_draft.get("_unavailable_product")

        if ambiguous_options:
            business_context += f" Ask the customer which product they mean: {', '.join(ambiguous_options)}"

        if unavailable_product:
            tool_result = {
                "success": False,
                "message": f"Sorry, {unavailable_product} is currently unavailable."
            }

        # ── 6. Response Generation ─────────────────────────────────────────
        if current_state == "awaiting_confirmation" and not tool_result:
            # Generate the structured spoken confirmation summary
            confirmation_text = order_draft_engine.build_confirmation_summary(session.order_draft)
            gen = generate_confirmation_prompt(
                confirmation_summary=confirmation_text,
                conversation_history=session.conversation_history,
            )
        else:
            gen = generate_response(
                customer_message=customer_message,
                conversation_history=session.conversation_history,
                intent=intent,
                tool_result=tool_result,
                missing_slots=missing_slots,
                business_context=business_context,
            )

        ai_response = gen["response"]
        total_tokens += gen.get("tokens_used", 0)

        # Clear one-shot context flags
        if ambiguous_options:
            session.order_draft.pop("_ambiguous_options", None)
        if unavailable_product:
            session.order_draft.pop("_unavailable_product", None)

        session.add_message(role="ai", message=ai_response)

        return ProcessResult(
            response=ai_response,
            intent=intent,
            intent_confidence=confidence,
            current_state=current_state,
            draft_status=session.order_draft.get("draft_status", "empty"),
            slots_collected=slots_collected,
            missing_slots=missing_slots,
            tool_executed=tool_executed,
            tool_result=tool_result,
            total_tokens_used=total_tokens,
        )


# Module-level singleton
conversation_engine = ConversationEngine()
