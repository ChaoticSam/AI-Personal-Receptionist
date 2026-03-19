from sqlalchemy import Column, String, ForeignKey, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.db.session import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2))
    unit = Column(String)
    is_available = Column(String, default="true")
    # Stores synonyms and custom fields: {"synonyms": [...], "custom_fields": [...]}
    product_meta = Column(JSONB, nullable=True, default=dict)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
