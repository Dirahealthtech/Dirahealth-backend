from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base
from .base import TimeStampMixin


# Association table for many-to-many relationship between homepage sections and products
homepage_section_products = Table(
    'homepage_section_products',
    Base.metadata,
    Column('homepage_section_id', Integer, ForeignKey('homepage_sections.id', ondelete='CASCADE'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id', ondelete='CASCADE'), primary_key=True)
)


class HomepageSection(Base, TimeStampMixin):
    """
    Homepage sections for organizing and displaying products on the homepage.
    Examples: "Flash Sales", "Black Friday Offers", "What's New", "Trending Now", etc.
    """
    __tablename__ = "homepage_sections"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)  # e.g., "Flash Sales", "Black Friday"
    slug = Column(String(100), nullable=False, unique=True, index=True)  # URL-friendly version
    description = Column(Text, nullable=True)  # Rich HTML description
    icon = Column(String(255), nullable=True)  # Icon URL or icon class
    background_color = Column(String(7), nullable=True)  # Hex color code #FF0000
    text_color = Column(String(7), nullable=True)  # Hex color code for text
    display_order = Column(Integer, default=0)  # Order on homepage
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)  # When section becomes active
    end_date = Column(DateTime, nullable=True)  # When section expires
    max_products = Column(Integer, default=10)  # Maximum products to show

    # Many-to-many relationship with products
    products = relationship("Product", secondary=homepage_section_products, back_populates="homepage_sections")

    def __repr__(self):
        return f"<HomepageSection(id={self.id}, title='{self.title}', active={self.is_active})>"
