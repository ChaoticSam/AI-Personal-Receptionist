from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from decimal import Decimal


class ProductMetadata(BaseModel):
    synonyms: Optional[List[str]] = []
    custom_fields: Optional[List[str]] = []


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    is_available: Optional[str] = "true"
    product_meta: Optional[ProductMetadata] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    is_available: Optional[str] = None
    product_meta: Optional[ProductMetadata] = None


class ProductResponse(BaseModel):
    id: UUID
    business_id: UUID
    name: str
    description: Optional[str] = None
    price: Optional[Decimal] = None
    unit: Optional[str] = None
    is_available: Optional[str] = None
    product_meta: Optional[ProductMetadata] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
