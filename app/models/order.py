from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, DateTime, Enum, JSON
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..enums import OrderStatus, PaymentMethod, PaymentStatus
from ..models.base import TimeStampMixin


class Order(Base, TimeStampMixin):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String, nullable=False, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    shipping_address = Column(JSON, nullable=False)
    billing_address = Column(JSON, nullable=False)
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    payment_transaction_id = Column(String, nullable=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_amount = Column(Float, nullable=False)
    payment_currency = Column(String, default="KES")
    payment_date = Column(DateTime, nullable=True)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, nullable=False)
    shipping_cost = Column(Float, nullable=False)
    discount = Column(Float, default=0)
    total = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    tracking_carrier = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=True)
    requires_verification = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")
    services = relationship("OrderService", back_populates="order")
    prescription = relationship("Prescription")
