from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..db.base import Base
from .base import TimeStampMixin


class Review(Base, TimeStampMixin):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Float, nullable=False)  # 1-5 star rating
    title = Column(String(200), nullable=True)
    comment = Column(Text, nullable=True)
    is_verified_purchase = Column(Boolean, default=False)  # True if user actually bought the product
    is_approved = Column(Boolean, default=True)  # For moderation
    helpful_votes = Column(Integer, default=0)

    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    review_votes = relationship("ReviewVote", back_populates="review", cascade="all, delete-orphan")


class ReviewVote(Base, TimeStampMixin):
    __tablename__ = "review_votes"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_helpful = Column(Boolean, nullable=False)  # True for helpful, False for not helpful

    # Relationships
    review = relationship("Review", back_populates="review_votes")
    user = relationship("User", back_populates="review_votes")

    # Ensure one vote per user per review
    __table_args__ = (
        {"extend_existing": True},
    )
