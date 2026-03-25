import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.session import Base


class AgentOrderDraft(Base):
    """Persists order-in-progress for ElevenLabs PSTN agent (one row per call)."""

    __tablename__ = "agent_order_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(
        UUID(as_uuid=True),
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)

    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    order_notes = Column(String, nullable=True)
    custom_fields = Column(JSONB, nullable=True, default=dict)

    status = Column(String, nullable=False, default="collecting")
    placed_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    last_idempotency_key = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
