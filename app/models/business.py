from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.session import Base

class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    business_type = Column(String)
    phone_number = Column(String, nullable=False)
    whatsapp_number = Column(String, nullable=True)
    timezone = Column(String)
    address = Column(String)
    voice_config = Column(JSONB, nullable=True, default=dict)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())