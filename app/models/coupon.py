from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime

from ..db.base import Base
from app.models.base import TimeStampMixin

class Coupon(Base, TimeStampMixin):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    discount_type = Column(String, nullable=False)  # percentage or fixed
    discount_value = Column(Float, nullable=False)  # Either percentage or fixed amount
    minimum_order_amount = Column(Float, nullable=True)  # Minimum order amount for coupon to apply
    maximum_discount = Column(Float, nullable=True)  # Maximum discount amount (for percentage type)
    valid_from = Column(DateTime, nullable=False, default=datetime.now)
    valid_to = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    usage_limit = Column(Integer, nullable=True)  # Maximum number of times coupon can be used
    times_used = Column(Integer, nullable=False, default=0)
    description = Column(String, nullable=True)