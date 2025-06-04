from sqlalchemy import Column, Integer, ForeignKey, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from ..models.base import TimeStampMixin

class Cart(Base, TimeStampMixin):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    applied_coupon_code = Column(String, nullable=True)
    discount_amount = Column(Float, default=0.0)
    discount_type = Column(String, nullable=True)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("User", back_populates="cart")
    cart_items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    cart_service_items = relationship("CartServiceItem", back_populates="cart", cascade="all, delete-orphan")