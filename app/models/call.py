from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=True)
    caller_phone = Column(String, nullable=False)
    call_sid = Column(String)
    status = Column(String, default="initiated", nullable=False)
    duration = Column(Integer)  # seconds; matches existing DB column type
    notes = Column(String)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

    # ElevenLabs Conversational AI linkage + captured transcript
    conversation_id = Column(String(128), nullable=True, index=True)
    transcript = Column(JSONB, nullable=True)  # [{role, message, time_in_call_secs}, ...]
    summary = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
