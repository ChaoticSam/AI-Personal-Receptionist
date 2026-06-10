import logging
from datetime import datetime, timezone
from app.models.call import Call
from app.models.customer import Customer
from app.models.order import Order

logger = logging.getLogger(__name__)


def _seconds_recent(dt):
    """Seconds since `dt` (timezone-aware or naive UTC); inf if None."""
    if dt is None:
        return float("inf")
    if dt.tzinfo is not None:
        return (datetime.now(timezone.utc) - dt).total_seconds()
    return (datetime.utcnow() - dt).total_seconds()


def create_call(db, business_id, customer_id, caller_phone, call_sid=None):

    call = Call(
        business_id=business_id,
        customer_id=customer_id,
        caller_phone=caller_phone,
        call_sid=call_sid,
        status="initiated"
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    print(f"Call created: id={call.id}, phone={call.caller_phone}, customer_id={call.customer_id}, business_id={call.business_id}")

    return call


def get_calls_by_business(db, business_id):

    calls = (
        db.query(Call)
        .filter(Call.business_id == business_id)
        .order_by(Call.created_at.desc())
        .all()
    )

    results = []
    for call in calls:
        # Prefer customer_id FK; fall back to phone lookup for older records
        if call.customer_id:
            customer = db.query(Customer).filter(Customer.id == call.customer_id).first()
        else:
            customer = (
                db.query(Customer)
                .filter(
                    Customer.phone == call.caller_phone,
                    Customer.business_id == business_id
                )
                .first()
            )

        linked_order = (
            db.query(Order)
            .filter(Order.call_id == call.id)
            .first()
        )

        results.append({
            "id": call.id,
            "business_id": call.business_id,
            "customer_id": call.customer_id,
            "caller_phone": call.caller_phone,
            "call_sid": call.call_sid,
            "status": call.status,
            "duration": call.duration,
            "notes": call.notes,
            "started_at": call.started_at,
            "ended_at": call.ended_at,
            "created_at": call.created_at,
            "customer_name": customer.name if customer else None,
            "linked_order_id": linked_order.id if linked_order else None,
        })

    return results


def _coerce_duration_secs(secs):
    """Normalize a duration to a non-negative int (seconds), or None."""
    try:
        secs = int(secs)
    except (TypeError, ValueError):
        return None
    return secs if secs >= 0 else None


def save_transcript_from_conversation(db, call, convo):
    """
    Persist an ElevenLabs conversation payload (from the Conversations API or the
    post-call webhook `data` object) onto a Call: transcript turns, summary,
    duration, conversation_id, and completed status. Returns the updated call.
    """
    from app.services.elevenlabs_platform import normalize_transcript

    turns = normalize_transcript(convo)
    if turns:
        call.transcript = turns

    analysis = convo.get("analysis") or {}
    summary = analysis.get("transcript_summary")
    if summary:
        call.summary = summary

    metadata = convo.get("metadata") or {}
    dur = _coerce_duration_secs(metadata.get("call_duration_secs"))
    if dur is not None:
        call.duration = dur

    cid = convo.get("conversation_id")
    if cid:
        call.conversation_id = cid

    # ElevenLabs status "done" -> our "completed"; keep terminal states sane.
    if convo.get("status") == "done" and call.status != "completed":
        call.status = "completed"
    if not call.ended_at:
        call.ended_at = datetime.utcnow()

    db.commit()
    db.refresh(call)
    return call


def get_call_for_business(db, call_id, business_id):
    """Fetch a single call scoped to a business, or None."""
    return (
        db.query(Call)
        .filter(Call.id == call_id, Call.business_id == business_id)
        .first()
    )


def get_call_detail(db, call_id, business_id):
    """
    Return a call as a dict including its transcript. If no transcript is stored
    yet but the call is linked to an ElevenLabs conversation, fetch it live and
    persist it so future loads are instant.
    """
    call = get_call_for_business(db, call_id, business_id)
    if not call:
        return None

    # Lazy backfill from ElevenLabs when we have a link but no stored transcript.
    if not call.transcript and call.conversation_id:
        try:
            from app.services.elevenlabs_platform import get_conversation_sync

            convo = get_conversation_sync(call.conversation_id)
            if convo:
                call = save_transcript_from_conversation(db, call, convo)
        except Exception as exc:  # never let a live-fetch failure break the page
            logger.warning("Live transcript fetch failed for call %s: %s", call_id, exc)

    customer = None
    if call.customer_id:
        customer = db.query(Customer).filter(Customer.id == call.customer_id).first()
    linked_order = db.query(Order).filter(Order.call_id == call.id).first()

    return {
        "id": call.id,
        "business_id": call.business_id,
        "customer_id": call.customer_id,
        "caller_phone": call.caller_phone,
        "call_sid": call.call_sid,
        "status": call.status,
        "duration": call.duration,
        "notes": call.notes,
        "summary": call.summary,
        "conversation_id": call.conversation_id,
        "transcript": call.transcript or [],
        "started_at": call.started_at,
        "ended_at": call.ended_at,
        "created_at": call.created_at,
        "customer_name": customer.name if customer else None,
        "linked_order_id": linked_order.id if linked_order else None,
    }


def end_call(db, call_id, transcript=None, summary=None):

    call = db.query(Call).filter(Call.id == call_id).first()

    if not call:
        return None

    call.status = "completed"
    call.ended_at = datetime.utcnow()

    if transcript:
        call.notes = f"Transcript:\n{transcript}"
    if summary:
        existing = call.notes or ""
        call.notes = existing + f"\n\nSummary:\n{summary}"

    db.commit()
    db.refresh(call)

    print(f"Call ended: id={call.id}, status={call.status}, ended_at={call.ended_at}")

    return call
