from sqlalchemy import Column, Integer, String, Text, Boolean, Float, ForeignKey, JSON, Enum, Table
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..enums import DeviceType, ServiceType
from app.models.base import TimeStampMixin


# Many-to-many relationship table between services and technicians
service_technician = Table(
    "service_technicians",
    Base.metadata,
    Column("service_id", Integer, ForeignKey("services.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)


class Service(Base, TimeStampMixin):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    service_type = Column(Enum(ServiceType), nullable=False)
    device_type = Column(Enum(DeviceType), nullable=False)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    technicians = relationship("User", secondary=service_technician)
    appointments = relationship("Appointment", back_populates="service")


    def __repr__(self):
        return f'<Service(name={self.name}, service_type={self.service_type}, device_type={self.device_type})>'
