from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from app.models.base import TimeStampMixin

class ShipmentTracking(Base, TimeStampMixin):
    __tablename__ = "shipment_trackings"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    status = Column(String, nullable=False)  
    location = Column(String, nullable=True)
    carrier = Column(String, nullable=True)
    estimated_delivery = Column(DateTime, nullable=True)
    tracking_number = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    notes = Column(String, nullable=True)
    
    # Relationships
    order = relationship("Order", back_populates="shipment_tracking")
    
    # Status checkpoints
    checkpoints = relationship("ShipmentCheckpoint", back_populates="shipment", 
                              order_by="ShipmentCheckpoint.timestamp", 
                              cascade="all, delete-orphan")