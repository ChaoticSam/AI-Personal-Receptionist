from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.call_schema import IncomingCallRequest, CallListItem
from app.services.customer_service import find_or_create_customer
from app.services.call_service import create_call, get_calls_by_business
from app.core.session_manager import session_manager

router = APIRouter()


@router.post("/calls/incoming")
def incoming_call(payload: IncomingCallRequest, db: Session = Depends(get_db)):

    customer = find_or_create_customer(
        db,
        business_id=payload.business_id,
        phone=payload.phone,
        name=payload.caller_name,
        email=None,
        notes=None
    )

    call = create_call(
        db,
        business_id=payload.business_id,
        customer_id=customer.id,
        caller_phone=payload.phone,
        call_sid=payload.call_sid
    )

    session_manager.create_session(
        call_id=str(call.id),
        business_id=str(call.business_id),
        customer_id=str(customer.id)
    )

    return {
        "call_id": str(call.id),
        "customer_id": str(customer.id)
    }


@router.get("/calls", response_model=List[CallListItem])
def list_calls(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_calls_by_business(db, current_user.business_id)
