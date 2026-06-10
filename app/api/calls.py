from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.call_schema import IncomingCallRequest, CallListItem, CallDetailResponse
from app.services.customer_service import find_or_create_customer
from app.services.call_service import create_call, get_calls_by_business, get_call_detail

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


@router.get("/calls/{call_id}", response_model=CallDetailResponse)
def get_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    detail = get_call_detail(db, call_id, current_user.business_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Call not found")
    return detail
