from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.enums import OrderStatus


# Supporting schemas for dashboard components
class TopSellingProduct(BaseModel):
    product_id: int
    name: str
    slug: str
    units_sold: int
    revenue: float


class LowStockProduct(BaseModel):
    product_id: int
    name: str
    slug: str
    stock_left: int
    reorder_level: Optional[int] = None


class CategorySummary(BaseModel):
    category_id: int
    name: str
    product_count: int
    revenue: float = 0.0


class TopBuyer(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: str
    total_spent: float
    total_orders: int
    last_order_date: Optional[datetime] = None


class LatestOrder(BaseModel):
    order_id: int
    order_number: str
    user_name: str
    status: OrderStatus
    total: float
    created_at: datetime


class RecentReview(BaseModel):
    review_id: int
    user_name: str
    product_name: str
    rating: float
    comment: str
    created_at: datetime


class RevenueByCategoryItem(BaseModel):
    category_id: int
    category_name: str
    revenue: float
    order_count: int


# Main dashboard response schemas
class SummaryStats(BaseModel):
    total_users: int
    total_products: int
    total_categories: int
    total_orders: int
    total_sales: float
    active_users_this_month: int
    conversion_rate: float


class SalesStats(BaseModel):
    today: float
    this_week: float
    this_month: float
    last_month: float
    year_to_date: float
    order_count_today: int
    order_count_this_week: int
    order_count_this_month: int
    average_order_value: float
    top_selling_products: List[TopSellingProduct]


class ProductStats(BaseModel):
    total: int
    active: int
    inactive: int
    out_of_stock: int
    low_stock_count: int
    low_stock_products: List[LowStockProduct]
    categories: List[CategorySummary]


class UserStats(BaseModel):
    total: int
    new_today: int
    new_this_week: int
    new_this_month: int
    active_this_month: int
    verified_users: int
    top_buyers: List[TopBuyer]


class OrderStats(BaseModel):
    pending: int
    confirmed: int
    shipped: int
    delivered: int
    cancelled: int
    returned: int
    total_value: float
    latest_orders: List[LatestOrder]


class ReviewStats(BaseModel):
    total_reviews: int
    average_rating: float
    reviews_this_month: int
    pending_reviews: int
    recent_reviews: List[RecentReview]


class SystemAlerts(BaseModel):
    low_stock_products: int
    out_of_stock_products: int
    pending_orders: int
    unread_reviews: int
    failed_payments: int


class DashboardResponse(BaseModel):
    summary: SummaryStats
    sales: SalesStats
    products: ProductStats
    users: UserStats
    orders: OrderStats
    reviews: ReviewStats
    revenue_by_category: List[RevenueByCategoryItem]
    alerts: SystemAlerts
    last_updated: datetime

    class Config:
        from_attributes = True
