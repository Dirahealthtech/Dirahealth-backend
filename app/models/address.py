from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
import enum

from ..db.base import Base
from ..models.base import TimeStampMixin
from ..enums import AddressType


class Address(Base, TimeStampMixin):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer_profiles.id"))
    address_type = Column(Enum(AddressType), default=AddressType.BOTH)
    street = Column(String, nullable=False)
    city = Column(String, nullable=False)
    country = Column(String, nullable=False)
    postal_code = Column(String, nullable=False)
    is_default = Column(Boolean, default=False)

    # Relationships
    customer = relationship("CustomerProfile", back_populates="addresses")
