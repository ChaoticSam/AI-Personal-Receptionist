from sqlalchemy import Column, String, Text, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

from app.db.session import Base
from app.config import EMBEDDING_DIMENSIONS


class ProductEmbedding(Base):
    __tablename__ = "product_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    business_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    # EMBEDDING_DIMENSIONS-dim vector from EMBEDDING_MODEL
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    # The text that was embedded — useful for debugging
    embed_text = Column(Text, nullable=False)

    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("product_id", name="uq_product_embedding_product_id"),
    )
