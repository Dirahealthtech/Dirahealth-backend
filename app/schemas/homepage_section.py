from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from .product import ProductResponse


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
