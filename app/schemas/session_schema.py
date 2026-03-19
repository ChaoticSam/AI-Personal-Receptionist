from pydantic import BaseModel
from typing import Optional, List, Any


class MessageRequest(BaseModel):
    role: str         # "customer" or "ai"
    message: str


class OrderDraftUpdate(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None


class ConfirmOrderRequest(BaseModel):
    customer_id: str
    product_id: Optional[str] = None
    quantity: int = 1
    order_notes: Optional[str] = None


class EndCallRequest(BaseModel):
    transcript: Optional[str] = None
    summary: Optional[str] = None


class ConversationMessage(BaseModel):
    role: str
    message: str
    timestamp: str


class SessionResponse(BaseModel):
    call_id: str
    business_id: str
    customer_id: str
    status: str
    state: str
    slots_required: List[str]
    start_time: str
    conversation_history: List[ConversationMessage]
    order_draft: dict


# ── AI Conversation Engine ─────────────────────────────────────────────────

class ProcessRequest(BaseModel):
    """Payload sent to POST /session/{call_id}/process"""
    message: str
    business_context: Optional[str] = ""


class ProcessResponse(BaseModel):
    """Response from the AI conversation engine"""
    call_id: str
    response: str
    intent: str
    intent_confidence: float
    current_state: str
    draft_status: str
    slots_collected: dict
    missing_slots: List[str]
    tool_executed: Optional[str] = None
    tool_result: Optional[dict] = None
    total_tokens_used: int
