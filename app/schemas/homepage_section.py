from pydantic import BaseModel, model_validator
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

    @model_validator(mode='before')
    @classmethod
    def extract_pricing_fields(cls, data):
        """Extract price and discounted_price from nested pricing structure"""
        if hasattr(data, '__dict__'):
            data_dict = {}
            for key, value in data.__dict__.items():
                if not key.startswith('_'):
                    data_dict[key] = value
            data = data_dict
        
        if isinstance(data, dict):
            # If pricing is nested, extract it
            if 'pricing' in data and isinstance(data['pricing'], dict):
                data['price'] = data['pricing'].get('price', 0.0)
                data['discounted_price'] = data['pricing'].get('discounted_price', 0.0)
            elif hasattr(data.get('pricing'), 'price'):
                # Handle case where pricing is a Pydantic object
                pricing = data['pricing']
                data['price'] = pricing.price
                data['discounted_price'] = pricing.discounted_price
        
        return data

    class Config:
        from_attributes = True


class SimplifiedHomepageSectionResponse(BaseModel):
    title: str
    display_order: int
    is_active: bool
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
    is_active: bool
    slug: str
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
