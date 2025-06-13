from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RETURNED = "returned"

class PaymentMethod(str, Enum):
    CASH_ON_DELIVERY = "cash_on_delivery"
    CREDIT_CARD = "credit_card"
    MPESA = "mpesa"
    BANK_TRANSFER = "bank_transfer"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    
class AddressSchema(BaseModel):
    """Schema for shipping and billing addresses"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None

class OrderCreate(BaseModel):
    """Schema for creating orders"""
    shipping_address: Dict[str, Any]
    billing_address: Dict[str, Any]
    payment_method: PaymentMethod
    shipping_cost: float = 0.0
    notes: Optional[str] = None
    prescription_id: Optional[int] = None

class OrderItemResponse(BaseModel):
    """Schema for order item responses"""
    id: int
    product_id: int
    product_name: str
    quantity: int
    price: float
    discount: float
    total: float
    
    class Config:
        from_attributes = True

class OrderServiceResponse(BaseModel):
    """Schema for order service responses"""
    id: int
    service_id: int
    service_name: str
    price: float
    appointment_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    status: OrderStatus
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    subtotal: float
    tax: float
    shipping_cost: float
    discount: float
    total: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class OrderDetail(OrderResponse):
    """Schema for detailed order responses"""
    shipping_address: Dict[str, Any]
    billing_address: Dict[str, Any]
    items: List[OrderItemResponse]
    services: List[OrderServiceResponse]
    notes: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: OrderStatus
    notes: Optional[str] = None

class OrderCancellationRequest(BaseModel):
    """Schema for requesting order cancellation"""
    reason: str = Field(..., min_length=5)