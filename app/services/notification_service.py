"""
Notification Service — sends WhatsApp messages via Twilio and logs them to the DB.

Flow:
  1. build_order_message()   → formats the notification text from order data
  2. send_whatsapp()         → dispatches via Twilio REST API
  3. notify_business()       → orchestrates lookup → build → send → log with retry
"""

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import (
    TWILIO_ACCOUNT_SID,
    TWILIO_AUTH_TOKEN,
    TWILIO_WHATSAPP_FROM,
    NOTIFICATION_MAX_RETRIES,
)
from app.models.notification import Notification


# ── Message builder ────────────────────────────────────────────────────────────

def build_order_message(order_data: dict) -> str:
    """
    Build a human-readable WhatsApp message for a new order.

    order_data keys (all optional with fallbacks):
        order_id, product_name, quantity, customer_name, customer_phone,
        deadline, custom_fields (dict), order_notes
    """
    order_id = order_data.get("order_id", "N/A")
    product = order_data.get("product_name") or "Unknown product"
    qty = order_data.get("quantity", 1)
    customer = order_data.get("customer_name") or "Unknown customer"
    phone = order_data.get("customer_phone") or "—"
    deadline = order_data.get("deadline") or "Not specified"
    notes = order_data.get("order_notes") or ""
    custom_fields: dict = order_data.get("custom_fields") or {}

    lines = [
        "🛎 *New Order Received!*",
        "",
        f"📦 *Product:* {product}  ×{qty}",
        f"👤 *Customer:* {customer}",
        f"📞 *Phone:* {phone}",
        f"⏰ *Deadline:* {deadline}",
    ]

    if custom_fields:
        lines.append("")
        lines.append("📝 *Custom Details:*")
        for field, value in custom_fields.items():
            lines.append(f"  • {field.replace('_', ' ').title()}: {value}")

    if notes:
        lines.append("")
        lines.append(f"💬 *Notes:* {notes}")

    lines += ["", f"🔖 Order ID: `{order_id}`"]
    return "\n".join(lines)


# ── Twilio send ────────────────────────────────────────────────────────────────

def send_whatsapp(to_number: str, message: str) -> tuple[bool, str]:
    """
    Send a WhatsApp message via Twilio.

    Returns (success: bool, sid_or_error: str)
    Raises no exceptions — always returns gracefully.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False, "Twilio credentials not configured."

    try:
        from twilio.rest import Client  # lazy import to avoid startup cost
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        # Ensure number has 'whatsapp:' prefix
        to_wa = to_number if to_number.startswith("whatsapp:") else f"whatsapp:{to_number}"

        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=to_wa,
            body=message,
        )
        return True, msg.sid
    except Exception as e:
        return False, str(e)


# ── DB logging ─────────────────────────────────────────────────────────────────

def _log_notification(
    db: Session,
    business_id: str,
    order_id: str | None,
    recipient: str,
    message: str,
    status: str,
    retries: int = 0,
    error_message: str | None = None,
    sent_at: datetime | None = None,
) -> Notification:
    record = Notification(
        business_id=business_id,
        order_id=order_id,
        channel="whatsapp",
        recipient=recipient,
        message=message,
        status=status,
        retries=retries,
        error_message=error_message,
        sent_at=sent_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ── Main orchestrator ──────────────────────────────────────────────────────────

def notify_business(
    db: Session,
    business_id: str,
    order_data: dict,
    max_retries: int = NOTIFICATION_MAX_RETRIES,
) -> dict:
    """
    Look up the business WhatsApp number, build + send the notification, and
    persist a log record with retry logic.

    Returns {"success": bool, "notification_id": str | None, "error": str | None}
    """
    from app.models.business import Business

    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        return {"success": False, "notification_id": None, "error": "Business not found."}

    whatsapp_number = business.whatsapp_number
    if not whatsapp_number:
        return {
            "success": False,
            "notification_id": None,
            "error": "Business has no WhatsApp number configured.",
        }

    message = build_order_message(order_data)
    order_id = order_data.get("order_id")

    last_error = None
    for attempt in range(1, max_retries + 1):
        success, result = send_whatsapp(whatsapp_number, message)

        if success:
            record = _log_notification(
                db=db,
                business_id=business_id,
                order_id=order_id,
                recipient=whatsapp_number,
                message=message,
                status="sent",
                retries=attempt - 1,
                sent_at=datetime.now(timezone.utc),
            )
            return {"success": True, "notification_id": str(record.id), "error": None}

        last_error = result
        print(f"[Notification] Attempt {attempt}/{max_retries} failed: {last_error}")

        if attempt < max_retries:
            time.sleep(2 ** attempt)  # exponential back-off: 2s, 4s, 8s ...

    # All retries exhausted
    record = _log_notification(
        db=db,
        business_id=business_id,
        order_id=order_id,
        recipient=whatsapp_number,
        message=message,
        status="failed",
        retries=max_retries,
        error_message=last_error,
    )
    return {"success": False, "notification_id": str(record.id), "error": last_error}
