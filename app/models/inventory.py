from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from ..enums import ReferenceModel, TransactionType
from ..models.base import Base, TimeStampMixin


class InventoryTransaction(Base, TimeStampMixin):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    quantity = Column(Integer, nullable=False)
    previous_stock = Column(Integer, nullable=False)
    new_stock = Column(Integer, nullable=False)
    reference = Column(String, nullable=False)
    reference_id = Column(Integer, nullable=True)
    reference_model = Column(Enum(ReferenceModel), nullable=False)
    unit_cost = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    performed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="inventory_transactions")
    performed_by = relationship("User")
