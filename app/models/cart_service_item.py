from sqlalchemy import Column, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..models.base import TimeStampMixin

class CartServiceItem(Base, TimeStampMixin):
    __tablename__ = "cart_service_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    appointment_details = Column(JSON, nullable=True)

    # Relationships
    cart = relationship("Cart", back_populates="cart_service_items")
    service = relationship("Service")