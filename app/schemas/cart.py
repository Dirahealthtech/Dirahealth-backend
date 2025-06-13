from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class CartItemBase(BaseModel):
    """Base schema for cart items"""
    product_id: int
    quantity: int = Field(ge=1, default=1)

class CartItemCreate(CartItemBase):
    """Schema for creating cart items"""
    pass

class CartItemResponse(BaseModel):
    """Schema for cart item responses"""
    id: int
    cart_id: int
    product_id: int
    quantity: int
    added_at: datetime
    product_name: str
    product_price: float
    product_image: Optional[str] = None
    
    class Config:
        from_attributes = True

class CartServiceItemBase(BaseModel):
    """Base schema for cart service items"""
    service_id: int
    appointment_details: Optional[Dict[str, Any]] = None

class CartServiceItemCreate(CartServiceItemBase):
    """Schema for creating cart service items"""
    pass

class CartServiceItemResponse(BaseModel):
    """Schema for cart service item responses"""
    id: int
    cart_id: int
    service_id: int
    appointment_details: Optional[Dict[str, Any]] = None
    service_name: str
    service_price: float
    
    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    """Schema for cart responses"""
    id: int
    customer_id: int
    applied_coupon_code: Optional[str] = None
    discount_amount: float = 0.0
    discount_type: Optional[str] = None
    last_active: datetime
    items: List[CartItemResponse] = []
    service_items: List[CartServiceItemResponse] = []
    subtotal: float
    discount: float
    total: float
    
    class Config:
        from_attributes = True