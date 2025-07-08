from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base

class OrderCancellation(Base):
    __tablename__ = "order_cancellations"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    cancelled_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    cancelled_at = Column(DateTime, default=datetime.utcnow)
    refund_status = Column(String, nullable=True)  # Status of any associated refund

    # Relationships
    order = relationship("Order", back_populates="cancellation")
    cancelled_by = relationship("User")