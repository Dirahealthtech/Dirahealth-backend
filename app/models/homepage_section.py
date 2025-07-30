from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base
from .base import TimeStampMixin


# Association table for many-to-many relationship between homepage sections and products
homepage_section_products = Table(
    'homepage_section_products',
    Base.metadata,
    Column('homepage_section_id', Integer, ForeignKey('homepage_sections.id'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True)
)


class HomepageSection(Base, TimeStampMixin):
    """
    Homepage sections for organizing and displaying products on the homepage.
    Examples: "Flash Sales", "Black Friday Offers", "What's New", "Trending Now", etc.
    """
    __tablename__ = "homepage_sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)  # e.g., "Flash Sales", "Black Friday"
    description = Column(Text, nullable=True)  # Rich HTML description
    display_order = Column(Integer, default=0)  # Order on homepage
    is_active = Column(Boolean, default=True)

    # Relationships
    products = relationship("Product", secondary=homepage_section_products, back_populates="homepage_sections")

    def __repr__(self):
        return f"<HomepageSection(id={self.id}, title='{self.title}', active={self.is_active})>"
