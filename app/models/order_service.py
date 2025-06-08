from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from ..db.base import Base
from app.models.base import TimeStampMixin


class OrderService(Base, TimeStampMixin):
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


    def __repr__(self):
        return f'<OrderService(id={self.id}, order_id={self.order_id}, service_id={self.service_id}, price={self.price})>'
