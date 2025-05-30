from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from ..models.base import Base
from ..enums import CustomerType


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    customer_type = Column(Enum(CustomerType), nullable=False)
    organization_name = Column(String, nullable=True)
    organization_position = Column(String, nullable=True)
    organization_registration = Column(String, nullable=True)
    medical_history = Column(JSON, nullable=True)  # Stores conditions and notes as JSON

    # Relationships
    user = relationship("User", back_populates="customer_profile")
    addresses = relationship("Address", back_populates="customer")
    prescriptions = relationship("Prescription", back_populates="customer")
