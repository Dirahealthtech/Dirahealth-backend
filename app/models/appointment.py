from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.base import Base, TimeStampMixin

class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class LocationType(str, enum.Enum):
    ON_SITE = "on_site"
    CUSTOMER_LOCATION = "customer_location"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"

class ReminderMethod(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"

class Appointment(Base, TimeStampMixin):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    technician_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scheduled_date = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    notes = Column(JSON, nullable=True)  # Stores customer, technician, and internal notes
    location_type = Column(Enum(LocationType), nullable=False)
    location_address = Column(JSON, nullable=True)  # Stores address details as JSON
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_amount = Column(Float, nullable=True)
    payment_transaction_id = Column(String, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_date = Column(DateTime, nullable=True)
    reminders = Column(JSON, nullable=True)  # Stores array of reminder objects

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="appointments")
    technician = relationship("User", foreign_keys=[technician_id], back_populates="technician_appointments")
    service = relationship("Service", back_populates="appointments")
    product = relationship("Product", backref="appointments")
    order_services = relationship("OrderService", back_populates="appointment")