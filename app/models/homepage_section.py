from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..db.base import Base
from .base import TimeStampMixin


class HomepageSection(Base, TimeStampMixin):
    """
    Homepage sections for organizing and displaying products on the homepage.
    Examples: "Flash Sales", "Black Friday Offers", "What's New", "Trending Now", etc.
    """
    __tablename__ = "homepage_sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Flash Sales", "Black Friday"
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

    # Relationships
    products = relationship("Product", back_populates="homepage_section")

    def __repr__(self):
        return f"<HomepageSection(id={self.id}, name='{self.name}', active={self.is_active})>"
