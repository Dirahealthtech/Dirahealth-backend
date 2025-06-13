from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..db.base import Base
from app.models.base import TimeStampMixin

class ShipmentCheckpoint(Base, TimeStampMixin):
    __tablename__ = "shipment_checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipment_trackings.id"), nullable=False)
    status = Column(String, nullable=False)
    location = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    shipment = relationship("ShipmentTracking", back_populates="checkpoints")