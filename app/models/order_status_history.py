from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from ..enums import OrderStatus

class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    previous_status = Column(String, nullable=False)
    new_status = Column(String, nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    changed_at = Column(DateTime, default=datetime.now, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="status_history")
    changed_by = relationship("User")