from sqlalchemy import Column, String, Integer, Float, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class AiInteraction(Base):
    __tablename__ = "ai_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(String, nullable=False, index=True)
    business_id = Column(String, nullable=False, index=True)
    customer_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    intent = Column(String, nullable=False)
    intent_confidence = Column(Float)
    tool_executed = Column(String, nullable=True)
    tool_success = Column(String, nullable=True)      # "true" | "false" | null
    tokens_used = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False, default=func.now())
