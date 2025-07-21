from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..db.base import Base
from app.models.base import TimeStampMixin

class Category(Base, TimeStampMixin):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    image = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    parent = relationship("Category", remote_side=[id], back_populates="subcategories")
    subcategories = relationship("Category", back_populates="parent")
    products = relationship("Product", back_populates="category")


    def __repr__(self):
        return f'<Category(id={self.id}, name={self.name}, parent_id={self.parent_id})>'
