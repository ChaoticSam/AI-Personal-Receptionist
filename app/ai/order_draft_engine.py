"""
Order Draft Engine — owns all draft state management during a live call.

Responsibilities:
  - Merge incoming slot values into the draft (latest input always wins)
  - Track draft_status through its state machine
  - Determine which required fields are still missing
  - Validate the draft before triggering confirmation
  - Generate the spoken confirmation summary

Draft status state machine:
  empty → product_selected → collecting_details → ready_for_confirmation → confirmed
"""


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

EMPTY = "empty"
PRODUCT_SELECTED = "product_selected"
COLLECTING_DETAILS = "collecting_details"
READY_FOR_CONFIRMATION = "ready_for_confirmation"
CONFIRMED = "confirmed"


class OrderDraftEngine:

    # ── Slot merging ──────────────────────────────────────────────────────

    def apply_slots(self, draft: dict, new_slots: dict) -> dict:
        """
        Merge new_slots into the draft. Always overrides previous values
        (latest customer input wins). Handles nested custom_fields correctly.

        Returns the set of keys that were actually updated.
        """
        updated = {}
        for key, value in new_slots.items():
            if value is None:
                continue
            if key == "custom_fields" and isinstance(value, dict):
                for cf_key, cf_val in value.items():
                    if cf_val is not None:
                        draft["custom_fields"][cf_key] = cf_val
                        updated[f"custom_fields.{cf_key}"] = cf_val
            elif key not in ("missing", "tokens_used"):
                draft[key] = value
                updated[key] = value
        return updated

    # ── Validation ────────────────────────────────────────────────────────

    def get_missing_fields(self, draft: dict) -> list[str]:
        """
        Return the list of required fields not yet filled.
        Checks: product_name, quantity, and all required_custom_fields.
        """
        missing = []
        required_custom_fields = draft.get("_required_custom_fields", [])

        if not draft.get("product_id"):
            missing.append("product_name")
        if not draft.get("quantity"):
            missing.append("quantity")
        for field in required_custom_fields:
            if not draft["custom_fields"].get(field):
                missing.append(field)

        return missing

    def validate(self, draft: dict) -> tuple[bool, list[str]]:
        """
        Validate draft completeness.
        Returns (is_valid, missing_fields).
        """
        missing = self.get_missing_fields(draft)
        return len(missing) == 0, missing

    # ── Status advancement ────────────────────────────────────────────────

    def advance_status(self, draft: dict) -> str:
        """
        Determine and set the correct draft_status based on current content.
        Returns the new status string.
        """
        if not draft.get("product_id"):
            status = EMPTY
        elif self.get_missing_fields(draft):
            required_custom_fields = draft.get("_required_custom_fields", [])
            if required_custom_fields:
                status = COLLECTING_DETAILS
            else:
                status = PRODUCT_SELECTED
        else:
            status = READY_FOR_CONFIRMATION

        draft["draft_status"] = status
        return status

    # ── Confirmation summary ──────────────────────────────────────────────

    def build_confirmation_summary(self, draft: dict) -> str:
        """
        Build the spoken confirmation prompt shown to the customer.
        Example: "Let me confirm — Custom Mug, quantity 2, text: Best Dad Ever. Is that correct?"
        """
        parts = []

        if draft.get("product_name"):
            parts.append(draft["product_name"])
        if draft.get("quantity"):
            parts.append(f"quantity {draft['quantity']}")
        for field, value in draft.get("custom_fields", {}).items():
            if value:
                parts.append(f"{field}: {value}")
        if draft.get("customer_notes"):
            parts.append(f"notes: {draft['customer_notes']}")

        summary = ", ".join(parts)
        return f"Let me confirm your order — {summary}. Is that correct?"

    # ── Reset ─────────────────────────────────────────────────────────────

    def reset(self, session):
        """Discard the current draft entirely and reset the session state."""
        session.reset_order_draft()


# Module-level singleton
order_draft_engine = OrderDraftEngine()
