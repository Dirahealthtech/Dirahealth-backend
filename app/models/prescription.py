from sqlalchemy import Column, Integer, String, ForeignKey, Text

from app.models.base import Base, TimeStampMixin


class Prescription(Base, TimeStampMixin):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer_profiles.id"))
    document_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=True)
    description = Column(Text, nullable=True)

    # Relationships
    customer = relationship("CustomerProfile", back_populates="prescriptions")