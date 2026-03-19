from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    channel = Column(String, nullable=False, default="whatsapp")  # whatsapp | sms | email
    recipient = Column(String, nullable=False)                    # E.164 number or email
    message = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")    # pending | sent | failed
    retries = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
