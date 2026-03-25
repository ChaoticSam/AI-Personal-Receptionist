"""CRUD and validation for `AgentOrderDraft` (ElevenLabs order flow)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.agent_order_draft import AgentOrderDraft
from app.services.agent_tool_helpers import (
    custom_fields_satisfied,
    product_for_business,
    required_custom_field_names,
)
from app.services.order_service import create_order


def get_draft_by_call(db: Session, call_id: UUID) -> AgentOrderDraft | None:
    return (
        db.query(AgentOrderDraft)
        .filter(AgentOrderDraft.call_id == call_id)
        .first()
    )


def get_or_create_draft(
    db: Session,
    *,
    call_id: UUID,
    business_id: UUID,
    customer_id: UUID,
) -> AgentOrderDraft:
    row = get_draft_by_call(db, call_id)
    if row:
        return row
    row = AgentOrderDraft(
        call_id=call_id,
        business_id=business_id,
        customer_id=customer_id,
        quantity=1,
        status="collecting",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def build_draft_summary(
    *,
    product_name: str | None,
    quantity: int,
    order_notes: str | None,
    custom_fields: dict | None,
) -> str:
    parts = []
    if product_name:
        parts.append(f"Product: {product_name}")
    parts.append(f"Quantity: {quantity}")
    if order_notes:
        parts.append(f"Notes: {order_notes}")
    if custom_fields:
        parts.append(f"Options: {custom_fields}")
    return " | ".join(parts) if parts else ""


def prepare_order(
    db: Session,
    *,
    business_id: UUID,
    call_id: UUID,
    customer_id: UUID,
    product_id: UUID | None,
    quantity: int,
    order_notes: str | None,
    custom_fields: dict | None,
) -> tuple[bool, list[str], str | None, str | None]:
    """
    Update draft and return (ready_for_confirmation, missing_fields, summary, product_name).
    """
    draft = get_or_create_draft(
        db, call_id=call_id, business_id=business_id, customer_id=customer_id
    )
    if draft.status == "placed":
        return False, ["order_already_placed"], None, None

    draft.quantity = max(1, int(quantity or 1))
    if order_notes is not None:
        draft.order_notes = order_notes.strip() or None
    if product_id is not None:
        p = product_for_business(db, product_id, business_id)
        if not p:
            return False, ["invalid_product_id"], None, None
        if (p.is_available or "true").lower() not in ("true", "1", "yes"):
            return False, ["product_unavailable"], None, None
        draft.product_id = product_id
    if custom_fields is not None:
        draft.custom_fields = custom_fields

    missing: list[str] = []
    if draft.product_id is None:
        missing.append("product_id")

    pname: str | None = None
    if draft.product_id:
        prod = product_for_business(db, draft.product_id, business_id)
        pname = prod.name if prod else None
        req = required_custom_field_names(prod) if prod else []
        miss_cf = custom_fields_satisfied(req, draft.custom_fields)
        for f in miss_cf:
            missing.append(f"custom_field:{f}")

    ready = len(missing) == 0
    draft.status = "ready_for_confirmation" if ready else "collecting"
    db.commit()
    db.refresh(draft)

    summary = build_draft_summary(
        product_name=pname,
        quantity=draft.quantity,
        order_notes=draft.order_notes,
        custom_fields=draft.custom_fields,
    )
    return ready, missing, summary, pname


def place_order(
    db: Session,
    *,
    business_id: UUID,
    call_id: UUID,
    customer_id: UUID,
    customer_confirmed: bool,
    idempotency_key: str,
    product_id: UUID,
    quantity: int,
    order_notes: str | None,
    custom_fields: dict | None,
) -> tuple[bool, str | None, bool]:
    """
    Returns (ok, error_or_none, idempotent_replay).
    """
    if not customer_confirmed:
        return False, "customer_confirmed_must_be_true", False

    draft = get_or_create_draft(
        db, call_id=call_id, business_id=business_id, customer_id=customer_id
    )

    # One order per call; any repeat place_order returns the existing order.
    if draft.placed_order_id is not None:
        return True, None, True

    p = product_for_business(db, product_id, business_id)
    if not p:
        return False, "invalid_product_id", False
    if (p.is_available or "true").lower() not in ("true", "1", "yes"):
        return False, "product_unavailable", False

    req = required_custom_field_names(p)
    cf = custom_fields if custom_fields is not None else (draft.custom_fields or {})
    miss = custom_fields_satisfied(req, cf)
    if miss:
        return False, f"missing_custom_fields:{','.join(miss)}", False

    qty = max(1, int(quantity or 1))
    notes = order_notes if order_notes is not None else draft.order_notes
    if notes:
        notes = notes.strip() or None

    order = create_order(
        db,
        business_id=business_id,
        customer_id=customer_id,
        quantity=qty,
        product_id=product_id,
        call_id=call_id,
        order_notes=notes,
    )

    draft.product_id = product_id
    draft.quantity = qty
    draft.order_notes = notes
    draft.custom_fields = cf
    draft.status = "placed"
    draft.placed_order_id = order.id
    draft.last_idempotency_key = idempotency_key
    db.commit()

    return True, None, False
