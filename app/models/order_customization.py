from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class OrderCustomization(Base):
    __tablename__ = "order_customizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String, nullable=False)    # e.g. "text", "image"
    field_value = Column(String, nullable=False)   # e.g. "Best Dad Ever"
    created_at = Column(DateTime, nullable=False, default=func.now())
