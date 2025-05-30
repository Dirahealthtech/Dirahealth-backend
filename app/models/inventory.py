from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.base import Base, TimeStampMixin

class TransactionType(str, enum.Enum):
    PURCHASE = "purchase"
    SALE = "sale"
    RETURN = "return"
    ADJUSTMENT = "adjustment"
    WRITE_OFF = "write_off"
    TRANSFER = "transfer"

class ReferenceModel(str, enum.Enum):
    ORDER = "Order"
    PURCHASE_ORDER = "PurchaseOrder"
    STOCK_ADJUSTMENT = "StockAdjustment"

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