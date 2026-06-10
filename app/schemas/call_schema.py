from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class IncomingCallRequest(BaseModel):
    business_id: str
    phone: str
    call_sid: Optional[str] = None
    caller_name: Optional[str] = "Unknown"


class CallResponse(BaseModel):
    id: UUID
    business_id: UUID
    customer_id: Optional[UUID] = None
    caller_phone: str
    call_sid: Optional[str] = None
    status: str
    duration: Optional[int] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CallListItem(BaseModel):
    id: UUID
    business_id: UUID
    customer_id: Optional[UUID] = None
    caller_phone: str
    call_sid: Optional[str] = None
    status: str
    duration: Optional[int] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    customer_name: Optional[str] = None
    linked_order_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class TranscriptTurn(BaseModel):
    role: str  # "user" | "agent"
    message: str
    time_in_call_secs: Optional[float] = None


class CallDetailResponse(BaseModel):
    id: UUID
    business_id: UUID
    customer_id: Optional[UUID] = None
    caller_phone: str
    call_sid: Optional[str] = None
    status: str
    duration: Optional[int] = None
    notes: Optional[str] = None
    summary: Optional[str] = None
    conversation_id: Optional[str] = None
    transcript: List[TranscriptTurn] = []
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    customer_name: Optional[str] = None
    linked_order_id: Optional[UUID] = None

    class Config:
        from_attributes = True
