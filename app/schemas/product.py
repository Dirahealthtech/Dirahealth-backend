from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: str
    category_id: int
    supplier_id: Optional[int] = None
    sku: str
    price: float
    discounted_price: Optional[float] = 0.0
    tax_rate: Optional[float] = 0.0
    stock: int = 0
    requires_prescription: bool = False
    is_active: bool = True
    images: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    reorder_level: Optional[int] = None
    warranty_period: Optional[int] = None
    warranty_unit: Optional[str] = None
    warranty_description: Optional[str] = None

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    sku: Optional[str] = None
    price: Optional[float] = None
    discounted_price: Optional[float] = None
    tax_rate: Optional[float] = None
    stock: Optional[int] = None
    requires_prescription: Optional[bool] = None
    is_active: Optional[bool] = None
    images: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, Any]] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    reorder_level: Optional[int] = None
    warranty_period: Optional[int] = None
    warranty_unit: Optional[str] = None
    warranty_description: Optional[str] = None

    @validator('supplier_id', pre=True)
    def validate_supplier_id(cls, v):
        """Convert supplier_id of 0 to None (no supplier)"""
        if v == 0:
            return None
        return v

class ProductResponse(ProductBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    size: int
    pages: int
    
    class Config:
        from_attributes = True