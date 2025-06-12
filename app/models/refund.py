from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base

class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    processed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, nullable=False)
    transaction_id = Column(String, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="refunds")
    processed_by = relationship("User")