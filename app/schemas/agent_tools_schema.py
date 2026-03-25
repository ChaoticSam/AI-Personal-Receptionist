from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- resolve_context ---


class ResolveContextRequest(BaseModel):
    to_number: str = Field(..., description="Twilio number that was dialed (E.164)")
    from_number: str = Field(..., description="Caller number (E.164)")
    call_sid: Optional[str] = Field(None, description="Twilio CallSid when available")


class ResolveContextResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    business_id: Optional[str] = None
    customer_id: Optional[str] = None
    call_id: Optional[str] = None
    business_name: Optional[str] = None


# --- list_products ---


class ListProductsRequest(BaseModel):
    business_id: str


class ProductToolItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: Optional[str] = None
    unit: Optional[str] = None
    is_available: str
    required_custom_field_names: list[str] = Field(default_factory=list)


class ListProductsResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    products: list[ProductToolItem] = Field(default_factory=list)


# --- prepare_order ---


class PrepareOrderRequest(BaseModel):
    business_id: str
    call_id: str
    customer_id: str
    product_id: Optional[str] = None
    quantity: int = 1
    order_notes: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None


class PrepareOrderResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    ready_for_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    draft_summary: Optional[str] = None
    product_name: Optional[str] = None


# --- place_order ---


class PlaceOrderRequest(BaseModel):
    business_id: str
    call_id: str
    customer_id: str
    customer_confirmed: bool = Field(
        ...,
        description="Must be true — agent only after explicit yes from caller",
    )
    idempotency_key: str = Field(..., min_length=8, max_length=256)
    product_id: str
    quantity: int = 1
    order_notes: Optional[str] = None
    custom_fields: Optional[dict[str, Any]] = None


class PlaceOrderResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    order_id: Optional[str] = None
    idempotent_replay: bool = False


# --- append_call_notes ---


class AppendCallNotesRequest(BaseModel):
    business_id: str
    call_id: str
    text: str = Field(..., min_length=1, max_length=20000)


class AppendCallNotesResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
