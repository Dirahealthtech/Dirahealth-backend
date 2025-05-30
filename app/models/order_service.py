from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base, TimeStampMixin


class OrderService(Base):
    __tablename__ = "order_services"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    price = Column(Float, nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)

    # Relationships
    order = relationship("Order", back_populates="services")
    service = relationship("Service")
    appointment = relationship("Appointment", back_populates="order_services")