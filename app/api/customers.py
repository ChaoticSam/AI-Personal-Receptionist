from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.customer_schema import CustomerCreate, CustomerResponse
from app.services.customer_service import create_customer, get_customers_by_business

router = APIRouter()

@router.post("/customers", response_model=CustomerResponse)
def create_customer_api(
    payload: CustomerCreate, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    customer = create_customer(
        db, 
        business_id=current_user.business_id, 
        name=payload.name, 
        phone=payload.phone, 
        email=payload.email, 
        notes=payload.notes
    )
    return customer

@router.get("/customers", response_model=List[CustomerResponse])
def list_customers_api(
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    customers = get_customers_by_business(db, current_user.business_id)
    return customers