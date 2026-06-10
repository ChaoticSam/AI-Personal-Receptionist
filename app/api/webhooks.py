"""
ElevenLabs post-call webhooks.

ElevenLabs POSTs a `post_call_transcription` event once a ConvAI call ends. We
verify the HMAC signature, then persist the transcript/summary/duration onto the
matching Call. Matching order:
  1. by conversation_id (set earlier by the resolve_context tool), else
  2. by dialed (agent) number -> business + caller number + recent time window, else
  3. create a fresh call so the transcript is never lost.

Configure in the ElevenLabs dashboard: Conversational AI -> Settings -> Webhooks,
pointing at  {SERVER_BASE_URL}/webhooks/elevenlabs/post-call  and put the shared
secret in ELEVENLABS_WEBHOOK_SECRET.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import timedelta

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import ELEVENLABS_WEBHOOK_SECRET
from app.db.session import SessionLocal
from app.models.call import Call
from app.services.agent_tool_helpers import resolve_business_by_twilio_to
from app.services.call_service import (
    _seconds_recent,
    create_call,
    save_transcript_from_conversation,
)
from app.services.customer_service import find_or_create_customer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks/elevenlabs", tags=["elevenlabs-webhooks"])

_RECENT_CALL_WINDOW = timedelta(minutes=60)


def _verify_signature(raw_body: bytes, sig_header: str | None) -> bool:
    """
    Validate the `elevenlabs-signature` header of the form  t=<unix>,v0=<hex>.
    Signed payload is  f"{t}.{raw_body}"  with HMAC-SHA256(secret).
    If no secret is configured we skip verification (dev only) and log a warning.
    """
    if not ELEVENLABS_WEBHOOK_SECRET:
        logger.warning("ELEVENLABS_WEBHOOK_SECRET not set — skipping signature check")
        return True
    if not sig_header:
        return False

    parts = dict(
        p.split("=", 1) for p in sig_header.split(",") if "=" in p
    )
    timestamp = parts.get("t")
    received = parts.get("v0")
    if not timestamp or not received:
        return False

    signed_payload = f"{timestamp}.{raw_body.decode('utf-8')}"
    expected = hmac.new(
        ELEVENLABS_WEBHOOK_SECRET.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received)


def _caller_phone(data: dict) -> str | None:
    """The customer's number for this call, from the webhook metadata."""
    phone = (data.get("metadata") or {}).get("phone_call") or {}
    caller = phone.get("external_number")
    return caller.strip() if caller else None


def _ensure_customer_linked(db: Session, call: Call, data: dict) -> None:
    """
    Find-or-create the caller in our customer DB by phone and link them to the
    call. Runs for every matched call (not just freshly created ones), so a call
    matched by conversation_id also gets its customer resolved/backfilled.
    """
    caller = _caller_phone(data) or (call.caller_phone or "").strip()
    if not caller or caller == "unknown":
        return

    # Backfill the call's caller number if it was a placeholder.
    if call.caller_phone in (None, "", "unknown"):
        call.caller_phone = caller

    customer = find_or_create_customer(db, business_id=call.business_id, phone=caller)
    if call.customer_id != customer.id:
        call.customer_id = customer.id
    db.commit()


def _find_call(db: Session, data: dict) -> Call | None:
    conversation_id = data.get("conversation_id")

    # 1. Linked via resolve_context.
    if conversation_id:
        call = db.query(Call).filter(Call.conversation_id == conversation_id).first()
        if call:
            return call

    metadata = data.get("metadata") or {}
    phone = metadata.get("phone_call") or {}
    dialed = phone.get("agent_number")  # the business's Twilio number
    caller = phone.get("external_number")  # the customer

    business = resolve_business_by_twilio_to(db, dialed) if dialed else None
    if not business:
        return None

    # 2. Most recent matching call for this business/caller.
    if caller:
        recent = (
            db.query(Call)
            .filter(Call.business_id == business.id, Call.caller_phone == caller.strip())
            .order_by(Call.created_at.desc())
            .first()
        )
        if recent and _seconds_recent(recent.created_at) < _RECENT_CALL_WINDOW.total_seconds():
            return recent

    # 3. Create one so the transcript is preserved.
    customer = find_or_create_customer(
        db,
        business_id=business.id,
        phone=(caller or "unknown").strip(),
        name=None,
        email=None,
        notes=None,
    )
    return create_call(
        db,
        business_id=business.id,
        customer_id=customer.id,
        caller_phone=(caller or "unknown").strip(),
        call_sid=None,
    )


@router.post("/post-call")
async def elevenlabs_post_call(
    request: Request,
    elevenlabs_signature: str | None = Header(None, alias="elevenlabs-signature"),
):
    raw = await request.body()
    if not _verify_signature(raw, elevenlabs_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
        )

    try:
        event = json.loads(raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if event.get("type") != "post_call_transcription":
        # Ack other event types (audio, failures) without processing.
        return {"ok": True, "ignored": event.get("type")}

    data = event.get("data") or {}

    db = SessionLocal()
    try:
        call = _find_call(db, data)
        if not call:
            logger.warning(
                "post_call webhook: no matching call/business for conversation %s",
                data.get("conversation_id"),
            )
            return {"ok": True, "matched": False}
        _ensure_customer_linked(db, call, data)
        save_transcript_from_conversation(db, call, data)
        logger.info(
            "post_call webhook: stored transcript for call %s (conversation %s)",
            call.id,
            data.get("conversation_id"),
        )
        return {"ok": True, "matched": True, "call_id": str(call.id)}
    finally:
        db.close()
