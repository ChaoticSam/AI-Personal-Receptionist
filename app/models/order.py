from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from datetime import timedelta

from app.db.session import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"))
    call_id = Column(UUID(as_uuid=True), ForeignKey("calls.id"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False, default=1)
    status = Column(String, default="pending", nullable=False)
    order_notes = Column(String)
    deadline = Column(DateTime, default=func.now() + timedelta(days=7))

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())