from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from .product import ProductResponse


# Simplified schemas for public API
class SimplifiedProductResponse(BaseModel):
    id: int
    slug: str
    name: str
    price: float
    discounted_price: Optional[float] = None
    images: Optional[str] = None

    class Config:
        from_attributes = True


class SimplifiedHomepageSectionResponse(BaseModel):
    title: str
    display_order: int
    id: int
    products: List[SimplifiedProductResponse] = []

    class Config:
        from_attributes = True


# Original detailed schemas
class HomepageSectionBase(BaseModel):
    title: str
    description: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class HomepageSectionCreate(HomepageSectionBase):
    product_ids: Optional[List[int]] = []


class HomepageSectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    product_ids: Optional[List[int]] = None


class HomepageSectionResponse(HomepageSectionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    products: List[ProductResponse] = []

    class Config:
        from_attributes = True


class HomepageSectionListResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    display_order: int
    is_active: bool
    product_count: int
    created_at: datetime

    class Config:
        from_attributes = True
