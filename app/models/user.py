from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship

from ..models.base import TimeStampMixin, Base
from ..enums import UserRole


class User(Base, TimeStampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CUSTOMER)
    is_verified = Column(Boolean, default=False)
    reset_password_token = Column(String, nullable=True)
    reset_password_expires = Column(DateTime, nullable=True)

    # Relationships
    customer_profile = relationship("CustomerProfile", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="customer")
    cart = relationship("Cart", back_populates="customer", uselist=False)
    appointments = relationship("Appointment", back_populates="customer")
    technician_appointments = relationship("Appointment", foreign_keys="Appointment.technician_id", back_populates="technician")
