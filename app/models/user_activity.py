from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String

from .base import TimeStampMixin
from ..db.base import Base
from ..enums import ActivityType


class UserActivity(Base, TimeStampMixin):
    """
    Represents a user activity event within the application.
    This model tracks various user interactions such as viewing products,
    purchasing items, and searching for products.
    """

    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    anonymous_id = Column(String, nullable=True)  # to track anonymous users
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    activity_type = Column(String(20), default=ActivityType.VIEW)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))


    def __repr__(self):
        return f'<UserActivity(user_id={self.user_id}, product_id={self.product_id}, activity_type={self.activity_type})>'
