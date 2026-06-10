from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerResponse(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None