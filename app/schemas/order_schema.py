from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class OrderStatusUpdate(BaseModel):
    status: str


class OrderCreate(BaseModel):
    customer_id: UUID
    product_id: Optional[UUID] = None
    call_id: Optional[UUID] = None
    quantity: int = 1
    order_notes: Optional[str] = None


class OrderResponse(BaseModel):
    id: UUID
    business_id: UUID
    customer_id: UUID
    product_id: Optional[UUID] = None
    call_id: Optional[UUID] = None
    quantity: int
    status: str
    order_notes: Optional[str] = None
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderListItem(BaseModel):
    id: UUID
    business_id: UUID
    customer_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    call_id: Optional[UUID] = None
    quantity: int
    status: str
    order_notes: Optional[str] = None
    deadline: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    product_name: Optional[str] = None

    class Config:
        from_attributes = True
