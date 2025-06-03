from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..enums import AppointmentStatus, LocationType, PaymentStatus
from ..models.base import TimeStampMixin


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
