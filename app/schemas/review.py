from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class ReviewBase(BaseModel):
    rating: float
    title: Optional[str] = None
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        """Validate rating is between 1 and 5"""
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ReviewCreate(ReviewBase):
    product_id: int


class ReviewUpdate(BaseModel):
    rating: Optional[float] = None
    title: Optional[str] = None
    comment: Optional[str] = None

    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v):
        """Validate rating is between 1 and 5"""
        if v is not None and not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v


class ReviewVoteCreate(BaseModel):
    is_helpful: bool


class ReviewVoteResponse(BaseModel):
    id: int
    review_id: int
    user_id: int
    is_helpful: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserReviewInfo(BaseModel):
    """Basic user info for review responses"""
    id: int
    first_name: str
    last_name: str


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: float
    title: Optional[str] = None
    comment: Optional[str] = None
    is_verified_purchase: bool
    is_approved: bool
    helpful_votes: int
    created_at: datetime
    updated_at: datetime
    user: UserReviewInfo

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    items: List[ReviewResponse]
    total: int
    page: int
    size: int
    pages: int
    average_rating: float
    rating_breakdown: dict  # {1: count, 2: count, 3: count, 4: count, 5: count}


class ProductReviewSummary(BaseModel):
    """Review summary for product listings"""
    total_reviews: int
    average_rating: float
    rating_breakdown: dict
