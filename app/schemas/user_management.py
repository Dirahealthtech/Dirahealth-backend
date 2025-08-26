from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum

from app.enums import UserRole, OrderStatus


class UserStatus(str, Enum):
    ACTIVE = "active"
    BANNED = "banned"
    SUSPENDED = "suspended"


class UserSummaryResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    role: UserRole
    is_verified: bool
    status: str = "active"  # Default status for existing users
    created_at: datetime
    updated_at: datetime
    
    # Statistics
    total_orders: int = 0
    total_spent: float = 0.0
    last_order_date: Optional[datetime] = None
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderSummaryResponse(BaseModel):
    id: int
    order_number: str
    status: OrderStatus
    total: float
    payment_status: str
    created_at: datetime
    items_count: int = 0

    class Config:
        from_attributes = True


class UserDetailResponse(UserSummaryResponse):
    # Additional detailed information
    customer_profile: Optional[dict] = None
    recent_orders: List[OrderSummaryResponse] = []
    total_reviews: int = 0
    account_created: datetime
    shipping_addresses: List[dict] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    users: List[UserSummaryResponse]
    total: int
    page: int
    per_page: int
    pages: int

    class Config:
        from_attributes = True


class UserActionRequest(BaseModel):
    user_id: int
    reason: Optional[str] = None


class BanUserRequest(BaseModel):
    reason: Optional[str] = None
    ban_duration_days: Optional[int] = None  # None means permanent ban


class UserActivityResponse(BaseModel):
    id: int
    user_id: int
    activity_type: str
    description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserSearchFilters(BaseModel):
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    is_verified: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    has_orders: Optional[bool] = None
    min_spent: Optional[float] = None
    max_spent: Optional[float] = None


class UserStatsResponse(BaseModel):
    total_users: int
    active_users: int
    banned_users: int
    verified_users: int
    unverified_users: int
    users_with_orders: int
    total_revenue: float
    avg_order_value: float
    registration_trend: dict  # Last 30 days registration count

    class Config:
        from_attributes = True
