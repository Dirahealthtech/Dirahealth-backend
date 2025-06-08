from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..enums import ReferenceModel, TransactionType
from ..models.base import TimeStampMixin


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

    # Relationships
    product = relationship("Product", back_populates="inventory_transactions")
    performed_by = relationship("User")


    def __repr__(self):
        return f'<Inventory(id={self.id}, product_id={self.product_id}, type={self.type})>'
