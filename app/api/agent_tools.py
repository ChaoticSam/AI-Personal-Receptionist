"""
HTTP tools for ElevenLabs Conversational AI (PSTN via Twilio native integration).

Auth: every request must send header `X-Agent-Key: <ELEVENLABS_AGENT_TOOL_SECRET>`.

ElevenLabs agent setup (webhook tools, method POST, JSON body):
  1. {PUBLIC_BASE_URL}/agent/tools/resolve_context
     Body: to_number, from_number, optional call_sid (Twilio CallSid).
     Returns: business_id, customer_id, call_id, business_name.
  2. {PUBLIC_BASE_URL}/agent/tools/list_products
     Body: business_id
  3. {PUBLIC_BASE_URL}/agent/tools/prepare_order
     Body: business_id, call_id, customer_id, optional product_id, quantity,
           order_notes, custom_fields (object — use keys from product.required_custom_field_names).
  4. {PUBLIC_BASE_URL}/agent/tools/place_order
     Body: business_id, call_id, customer_id, customer_confirmed (must be true),
           idempotency_key (unique string per place attempt), product_id, quantity,
           optional order_notes, custom_fields.
     Only call after the caller explicitly confirms (e.g. says yes).
  5. {PUBLIC_BASE_URL}/agent/tools/append_call_notes
     Body: business_id, call_id, text (transcript snippet or summary).

Database: run scripts/sql/agent_order_drafts.sql on Postgres before first use.

Create the ElevenLabs agent (prompt + webhook tools) in code:
  python scripts/create_elevenlabs_receptionist_agent.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import ELEVENLABS_AGENT_TOOL_SECRET
from app.db.dependencies import get_db
from app.models.call import Call
from app.schemas.agent_tools_schema import (
    AppendCallNotesRequest,
    AppendCallNotesResponse,
    ListProductsRequest,
    ListProductsResponse,
    PlaceOrderRequest,
    PlaceOrderResponse,
    PrepareOrderRequest,
    PrepareOrderResponse,
    ProductToolItem,
    ResolveContextRequest,
    ResolveContextResponse,
)
from app.services.agent_order_draft_service import (
    get_draft_by_call,
    place_order,
    prepare_order,
)
from app.services.agent_tool_helpers import (
    assert_call_belongs,
    parse_uuid,
    required_custom_field_names,
    resolve_business_by_twilio_to,
)
from app.services.call_service import create_call
from app.services.customer_service import find_or_create_customer
from app.services.product_service import get_products_by_business

router = APIRouter(prefix="/agent/tools", tags=["elevenlabs-agent-tools"])

_RECENT_CALL_WINDOW = timedelta(minutes=30)


def _seconds_since(dt: datetime | None) -> float:
    if dt is None:
        return float("inf")
    if dt.tzinfo is not None:
        return (datetime.now(timezone.utc) - dt).total_seconds()
    return (datetime.utcnow() - dt).total_seconds()


def verify_agent_tool_secret(
    x_agent_key: str | None = Header(None, alias="X-Agent-Key"),
) -> None:
    if not ELEVENLABS_AGENT_TOOL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ELEVENLABS_AGENT_TOOL_SECRET is not configured",
        )
    if not x_agent_key or x_agent_key != ELEVENLABS_AGENT_TOOL_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Agent-Key",
        )


@router.post("/resolve_context", response_model=ResolveContextResponse)
def agent_resolve_context(
    payload: ResolveContextRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_agent_tool_secret),
) -> ResolveContextResponse:
    business = resolve_business_by_twilio_to(db, payload.to_number)
    if not business:
        return ResolveContextResponse(
            ok=False,
            error="no_business_for_to_number",
        )

    customer = find_or_create_customer(
        db,
        business_id=business.id,
        phone=payload.from_number.strip(),
        name=None,
        email=None,
        notes=None,
    )

    call = None
    if payload.call_sid:
        call = (
            db.query(Call)
            .filter(
                Call.call_sid == payload.call_sid,
                Call.business_id == business.id,
            )
            .first()
        )
    if not call:
        recent = (
            db.query(Call)
            .filter(
                Call.business_id == business.id,
                Call.caller_phone == payload.from_number.strip(),
                Call.status == "initiated",
            )
            .order_by(Call.created_at.desc())
            .first()
        )
        if recent and _seconds_since(recent.created_at) < _RECENT_CALL_WINDOW.total_seconds():
            call = recent
    if not call:
        call = create_call(
            db,
            business_id=business.id,
            customer_id=customer.id,
            caller_phone=payload.from_number.strip(),
            call_sid=payload.call_sid,
        )

    return ResolveContextResponse(
        ok=True,
        business_id=str(business.id),
        customer_id=str(customer.id),
        call_id=str(call.id),
        business_name=business.name,
    )


@router.post("/list_products", response_model=ListProductsResponse)
def agent_list_products(
    payload: ListProductsRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_agent_tool_secret),
) -> ListProductsResponse:
    try:
        bid = parse_uuid(payload.business_id, "business_id")
    except ValueError:
        return ListProductsResponse(ok=False, error="invalid_business_id")

    rows = get_products_by_business(db, bid)[:80]
    items: list[ProductToolItem] = []
    for p in rows:
        price_s = str(p.price) if p.price is not None else None
        items.append(
            ProductToolItem(
                id=str(p.id),
                name=p.name,
                description=(p.description or "")[:500] or None,
                price=price_s,
                unit=p.unit,
                is_available=p.is_available or "true",
                required_custom_field_names=required_custom_field_names(p),
            )
        )
    return ListProductsResponse(ok=True, products=items)


@router.post("/prepare_order", response_model=PrepareOrderResponse)
def agent_prepare_order(
    payload: PrepareOrderRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_agent_tool_secret),
) -> PrepareOrderResponse:
    try:
        bid = parse_uuid(payload.business_id, "business_id")
        cid = parse_uuid(payload.call_id, "call_id")
        cust = parse_uuid(payload.customer_id, "customer_id")
    except ValueError as e:
        return PrepareOrderResponse(ok=False, error=str(e))

    try:
        assert_call_belongs(db, call_id=cid, business_id=bid, customer_id=cust)
    except (LookupError, PermissionError) as e:
        return PrepareOrderResponse(ok=False, error=str(e))

    pid = None
    if payload.product_id:
        try:
            pid = parse_uuid(payload.product_id, "product_id")
        except ValueError:
            return PrepareOrderResponse(ok=False, error="invalid_product_id")

    ready, missing, summary, pname = prepare_order(
        db,
        business_id=bid,
        call_id=cid,
        customer_id=cust,
        product_id=pid,
        quantity=payload.quantity,
        order_notes=payload.order_notes,
        custom_fields=payload.custom_fields,
    )

    return PrepareOrderResponse(
        ok=True,
        ready_for_confirmation=ready,
        missing_fields=missing,
        draft_summary=summary,
        product_name=pname,
    )


@router.post("/place_order", response_model=PlaceOrderResponse)
def agent_place_order(
    payload: PlaceOrderRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_agent_tool_secret),
) -> PlaceOrderResponse:
    try:
        bid = parse_uuid(payload.business_id, "business_id")
        cid = parse_uuid(payload.call_id, "call_id")
        cust = parse_uuid(payload.customer_id, "customer_id")
        pid = parse_uuid(payload.product_id, "product_id")
    except ValueError as e:
        return PlaceOrderResponse(ok=False, error=str(e))

    try:
        assert_call_belongs(db, call_id=cid, business_id=bid, customer_id=cust)
    except (LookupError, PermissionError) as e:
        return PlaceOrderResponse(ok=False, error=str(e))

    ok, err, replay = place_order(
        db,
        business_id=bid,
        call_id=cid,
        customer_id=cust,
        customer_confirmed=payload.customer_confirmed,
        idempotency_key=payload.idempotency_key,
        product_id=pid,
        quantity=payload.quantity,
        order_notes=payload.order_notes,
        custom_fields=payload.custom_fields,
    )
    if not ok:
        return PlaceOrderResponse(ok=False, error=err)

    draft = get_draft_by_call(db, cid)
    oid = str(draft.placed_order_id) if draft and draft.placed_order_id else None
    return PlaceOrderResponse(ok=True, order_id=oid, idempotent_replay=replay)


@router.post("/append_call_notes", response_model=AppendCallNotesResponse)
def agent_append_call_notes(
    payload: AppendCallNotesRequest,
    db: Session = Depends(get_db),
    _: None = Depends(verify_agent_tool_secret),
) -> AppendCallNotesResponse:
    try:
        bid = parse_uuid(payload.business_id, "business_id")
        cid = parse_uuid(payload.call_id, "call_id")
    except ValueError as e:
        return AppendCallNotesResponse(ok=False, error=str(e))

    call = db.query(Call).filter(Call.id == cid).first()
    if not call or call.business_id != bid:
        return AppendCallNotesResponse(ok=False, error="call_not_found")

    block = payload.text.strip()
    prev = (call.notes or "").strip()
    call.notes = (prev + "\n\n" + block).strip() if prev else block
    db.commit()
    return AppendCallNotesResponse(ok=True)
