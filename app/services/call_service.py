from datetime import datetime
from app.models.call import Call
from app.models.customer import Customer
from app.models.order import Order


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
