from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from app.models.base import TimeStampMixin

class PurchaseOrder(Base, TimeStampMixin):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, nullable=False, unique=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    order_date = Column(DateTime, default=datetime.now(timezone.utc))
    expected_delivery_date = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    payment_status = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseOrderItem", back_populates="purchase_order")
    created_by = relationship("User")
