from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.order_schema import OrderCreate, OrderResponse, OrderListItem, OrderStatusUpdate
from app.services.order_service import create_order, get_orders_by_business, update_order_status

router = APIRouter()


@router.post("/orders", response_model=OrderResponse)
def create_order_api(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = create_order(
        db,
        business_id=current_user.business_id,
        customer_id=payload.customer_id,
        product_id=payload.product_id,
        call_id=payload.call_id,
        quantity=payload.quantity,
        order_notes=payload.order_notes
    )
    return order


@router.get("/orders", response_model=List[OrderListItem])
def list_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return get_orders_by_business(db, current_user.business_id)


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def patch_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = update_order_status(db, order_id, payload.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
