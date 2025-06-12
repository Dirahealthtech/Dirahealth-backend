from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CouponBase(BaseModel):
    """Base schema for coupons"""
    code: str
    discount_type: str = Field(..., description="Either 'percentage' or 'fixed'")
    discount_value: float = Field(gt=0, description="Percentage or fixed amount")
    minimum_order_amount: Optional[float] = Field(None, gt=0, description="Minimum order amount required")
    maximum_discount: Optional[float] = Field(None, gt=0, description="Maximum discount for percentage types")
    valid_from: datetime
    valid_to: datetime
    is_active: bool = True
    usage_limit: Optional[int] = Field(None, gt=0, description="Maximum number of times coupon can be used")
    description: Optional[str] = None

class CouponCreate(CouponBase):
    """Schema for creating coupons"""
    pass

class CouponUpdate(BaseModel):
    """Schema for updating coupons"""
    code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = Field(None, gt=0)
    minimum_order_amount: Optional[float] = Field(None, gt=0)
    maximum_discount: Optional[float] = Field(None, gt=0)
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: Optional[bool] = None
    usage_limit: Optional[int] = Field(None, gt=0)
    description: Optional[str] = None

class CouponResponse(CouponBase):
    """Schema for coupon responses"""
    id: int
    times_used: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True