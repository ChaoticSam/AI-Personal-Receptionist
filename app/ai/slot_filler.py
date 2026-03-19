"""
Hybrid Slot Extraction Engine — orchestrates rule-based + LLM extraction.

Architecture (per the slot_extraction_engine.docx spec):

  Customer message
       ↓
  Rule-based extractor   (<5ms, no LLM cost)
       ↓
  Decide: is LLM needed?
       ↓ (only if needed)
  LLM extractor          (~300ms, cheap model)
       ↓
  Merge layer            (rule-based overrides LLM where both present)
       ↓
  Validated slots

LLM is skipped when:
  - product_name is already known (resolved by product_matcher)
  - Rules extracted all needed slots (quantity + all custom_fields filled)
  - The AI just asked for one specific slot (context-aware mode)

LLM is always called when:
  - product_name is needed and not yet in draft
  - Input is complex / multi-slot / ambiguous (rules found nothing)
"""

from app.ai.rule_based_extractor import rule_extract
from app.ai.llm_extractor import llm_extract


# ---------------------------------------------------------------------------
# Decision logic — should we call the LLM?
# ---------------------------------------------------------------------------

def _needs_llm(
    customer_message: str,
    rule_slots: dict,
    existing_draft: dict,
    required_custom_fields: list[str],
    expected_slot: str | None,
) -> bool:
    """
    Return True if LLM extraction is needed.

    LLM is SKIPPED when:
      1. Context-aware mode AND rules already captured the expected slot
      2. product_name already in draft AND all required_custom_fields have values
         AND quantity is present → everything is known, nothing left for LLM

    LLM is CALLED when:
      1. product_name is unknown and not yet matched
      2. Rules found nothing at all (ambiguous input)
      3. At least one required custom field is still missing after rules
    """
    product_already_known = bool(existing_draft.get("product_id"))

    # Context-aware: AI just asked for one thing, rules got it
    if expected_slot and rule_slots.get("rule_extracted"):
        # Check the specific slot was filled
        if expected_slot == "quantity" and rule_slots.get("quantity"):
            return False
        if expected_slot in ("text", "message", "content"):
            cf = rule_slots.get("custom_fields", {})
            if cf.get(expected_slot):
                return False
        if expected_slot == "deadline" and rule_slots.get("deadline"):
            return False
        # Generic custom field captured
        if rule_slots.get("custom_fields", {}).get(expected_slot):
            return False

    # product_name unknown → LLM needed to identify it from messy speech
    if not product_already_known:
        return True

    # Product known — check if we still have missing required slots
    qty_known = bool(existing_draft.get("quantity") or rule_slots.get("quantity"))
    cf_in_draft = existing_draft.get("custom_fields", {})
    cf_in_rules = rule_slots.get("custom_fields", {})

    for field in required_custom_fields:
        if not cf_in_draft.get(field) and not cf_in_rules.get(field):
            # Still missing — but if rules found nothing at all, LLM might help
            if not rule_slots.get("rule_extracted"):
                return True

    if not qty_known and not rule_slots.get("rule_extracted"):
        return True

    return False


# ---------------------------------------------------------------------------
# Merge layer — rule-based takes priority over LLM
# ---------------------------------------------------------------------------

def _merge(rule_slots: dict, llm_slots: dict) -> dict:
    """
    Merge rule and LLM outputs. Rule-based values always override LLM values.
    custom_fields are merged at the key level (not wholesale replaced).
    """
    merged = dict(llm_slots)  # Start with LLM as base

    # Override with rule-based values
    for key, value in rule_slots.items():
        if key in ("rule_extracted", "tokens_used"):
            continue
        if key == "custom_fields" and isinstance(value, dict):
            merged_cf = dict(merged.get("custom_fields") or {})
            merged_cf.update(value)   # rule overrides LLM per key
            merged["custom_fields"] = merged_cf
        elif value is not None:
            merged[key] = value

    merged["tokens_used"] = rule_slots.get("tokens_used", 0) + llm_slots.get("tokens_used", 0)
    merged["rule_extracted"] = rule_slots.get("rule_extracted", False)
    return merged


# ---------------------------------------------------------------------------
# Public interface (same signature as before — drop-in replacement)
# ---------------------------------------------------------------------------

def extract_slots(
    customer_message: str,
    conversation_history: list,
    existing_draft: dict,
    required_custom_fields: list[str] | None = None,
    expected_slot: str | None = None,
) -> dict:
    """
    Hybrid slot extraction pipeline.

    Args:
        customer_message:      Raw customer utterance.
        conversation_history:  Full session turns so far.
        existing_draft:        Current order_draft (private _ keys stripped before sending to LLM).
        required_custom_fields: Product-specific fields from product_meta.custom_fields.
        expected_slot:         The slot the AI most recently asked for (enables context-aware mode).

    Returns:
        dict with:
          product_name, quantity, deadline, customer_notes, custom_fields,
          missing, tokens_used, rule_extracted (bool)
    """
    required_custom_fields = required_custom_fields or []

    # ── Step 1: Rule-based extraction (always runs, always fast) ───────────
    rule_slots = rule_extract(
        text=customer_message,
        required_custom_fields=required_custom_fields,
        expected_slot=expected_slot,
    )

    # ── Step 2: Decide whether LLM is needed ───────────────────────────────
    use_llm = _needs_llm(
        customer_message=customer_message,
        rule_slots=rule_slots,
        existing_draft=existing_draft,
        required_custom_fields=required_custom_fields,
        expected_slot=expected_slot,
    )

    if use_llm:
        llm_slots = llm_extract(
            customer_message=customer_message,
            conversation_history=conversation_history,
            existing_draft=existing_draft,
            required_custom_fields=required_custom_fields,
        )
        result = _merge(rule_slots, llm_slots)
    else:
        # Rule-based only — build a full result dict with safe defaults
        result = {
            "product_name": rule_slots.get("product_name", None),
            "quantity": rule_slots.get("quantity", None),
            "deadline": rule_slots.get("deadline", None),
            "customer_notes": rule_slots.get("customer_notes", None),
            "custom_fields": rule_slots.get("custom_fields", {}),
            "missing": [],
            "tokens_used": 0,
            "rule_extracted": True,
        }

    # Ensure all expected keys exist with safe defaults
    result.setdefault("product_name", None)
    result.setdefault("quantity", None)
    result.setdefault("deadline", None)
    result.setdefault("customer_notes", None)
    result.setdefault("custom_fields", {})
    result.setdefault("missing", [])
    result.setdefault("tokens_used", 0)
    result.setdefault("rule_extracted", False)

    return result
