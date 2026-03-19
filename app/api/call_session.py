import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.dependencies import get_db
from app.core.session_manager import session_manager
from app.schemas.session_schema import (
    MessageRequest, OrderDraftUpdate, ConfirmOrderRequest,
    EndCallRequest, SessionResponse, ProcessRequest, ProcessResponse
)
from app.services.order_service import create_order
from app.services.call_service import end_call
from app.ai.conversation_engine import conversation_engine

router = APIRouter(prefix="/session", tags=["call-session"])


def _get_session_or_404(call_id: str):
    session = session_manager.get_session(call_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"No active session for call_id={call_id}")
    return session


@router.get("/{call_id}", response_model=SessionResponse)
def get_session(call_id: str):
    """Return current state of an active call session."""
    session = _get_session_or_404(call_id)
    return session.to_dict()


@router.post("/{call_id}/message")
def add_message(call_id: str, payload: MessageRequest):
    """Append a customer or AI message to the conversation history."""
    session = _get_session_or_404(call_id)
    session.add_message(role=payload.role, message=payload.message)
    return {
        "call_id": call_id,
        "message_count": len(session.conversation_history)
    }


@router.patch("/{call_id}/order-draft")
def update_order_draft(call_id: str, payload: OrderDraftUpdate):
    """Update order draft fields as the customer describes their order."""
    session = _get_session_or_404(call_id)
    session.update_order_draft(payload.model_dump(exclude_none=True))
    return {
        "call_id": call_id,
        "order_draft": session.order_draft
    }


@router.post("/{call_id}/confirm-order")
def confirm_order(call_id: str, payload: ConfirmOrderRequest, db: Session = Depends(get_db)):
    """Customer confirmed the order — save it to the database."""
    session = _get_session_or_404(call_id)

    order = create_order(
        db,
        business_id=session.business_id,
        customer_id=payload.customer_id,
        product_id=payload.product_id,
        call_id=call_id,
        quantity=payload.quantity,
        order_notes=payload.order_notes
    )

    session.order_draft["confirmed"] = True
    session.order_draft["order_id"] = str(order.id)

    return {
        "call_id": call_id,
        "order_id": str(order.id),
        "status": "order confirmed"
    }


@router.post("/{call_id}/process", response_model=ProcessResponse)
def process_message(call_id: str, payload: ProcessRequest, db: Session = Depends(get_db)):
    """
    Main AI conversation endpoint.
    Accepts a customer message, runs the full AI pipeline
    (intent → slot fill → tool → response), and returns the AI reply.
    """
    session = _get_session_or_404(call_id)
    start = time.time()

    result = conversation_engine.process(
        customer_message=payload.message,
        session=session,
        db=db,
        business_context=payload.business_context or "",
    )

    latency_ms = int((time.time() - start) * 1000)

    # Persist observability record asynchronously (best-effort, non-blocking)
    try:
        from app.models.ai_interaction import AiInteraction
        interaction = AiInteraction(
            call_id=call_id,
            business_id=session.business_id,
            customer_message=payload.message,
            ai_response=result.response,
            intent=result.intent,
            intent_confidence=result.intent_confidence,
            tool_executed=result.tool_executed,
            tool_success=str(result.tool_result.get("success")).lower() if result.tool_result else None,
            tokens_used=result.total_tokens_used,
            latency_ms=latency_ms,
        )
        db.add(interaction)
        db.commit()
    except Exception as e:
        print(f"Failed to save ai_interaction: {e}")

    return ProcessResponse(
        call_id=call_id,
        response=result.response,
        intent=result.intent,
        intent_confidence=result.intent_confidence,
        current_state=result.current_state,
        draft_status=result.draft_status,
        slots_collected=result.slots_collected,
        missing_slots=result.missing_slots,
        tool_executed=result.tool_executed,
        tool_result=result.tool_result,
        total_tokens_used=result.total_tokens_used,
    )


@router.post("/{call_id}/end")
def end_call_session(call_id: str, payload: EndCallRequest, db: Session = Depends(get_db)):
    """End the call: update DB record, save transcript/summary, destroy session."""
    session = _get_session_or_404(call_id)

    end_call(
        db,
        call_id=call_id,
        transcript=payload.transcript,
        summary=payload.summary
    )

    session_manager.end_session(call_id)

    return {
        "call_id": call_id,
        "status": "call ended",
        "messages": len(session.conversation_history)
    }
