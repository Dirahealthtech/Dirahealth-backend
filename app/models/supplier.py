from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, Enum
from sqlalchemy.orm import relationship

from ..enums import SupplierStatus
from app.models.base import Base, TimeStampMixin


class Supplier(Base, TimeStampMixin):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_person = Column(JSON, nullable=True)  # Stores name, email, phone, position
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    address = Column(JSON, nullable=True)  # Stores address details as JSON
    tax_id = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    lead_time = Column(Integer, nullable=True)  # in days
    minimum_order_amount = Column(Float, nullable=True)
    website = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(SupplierStatus), default=SupplierStatus.ACTIVE)

    # Relationships
    products = relationship("Product", back_populates="manufacturer")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
