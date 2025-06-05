from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from ..models.base import TimeStampMixin


class Prescription(Base, TimeStampMixin):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer_profiles.id"))
    document_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.now(timezone.utc))
    expiry_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    customer = relationship("CustomerProfile", back_populates="prescriptions")


    def __repr__(self):
        return f'<Prescription(id={self.id}, customer_id={self.customer_id})>'
