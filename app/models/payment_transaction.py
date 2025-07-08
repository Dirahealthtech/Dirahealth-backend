from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from ..enums import PaymentMethod, PaymentStatus

class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    transaction_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="KES")
    method = Column(String, nullable=False)  # PaymentMethod as string
    status = Column(String, nullable=False)  # PaymentStatus as string
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="transactions")