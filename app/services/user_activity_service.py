from sqlalchemy import cast, desc, func, select, or_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String
from typing import List, Optional

from ..models import OrderItem, Product, User, UserActivity


class UserActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def get_top_picks(self, user: Optional[User] = None, anonymous_id: Optional[str] = None):
        # Get categories of products the user interacted with
        stmt = select(Product.category_id).join(UserActivity, Product.id == UserActivity.product_id)

        if user:
            stmt = stmt.where(UserActivity.user_id == user.id)
        elif anonymous_id:
            stmt = stmt.where(UserActivity.anonymous_id == anonymous_id)
        else:
            return []  # no activity data

        stmt = stmt.order_by(UserActivity.timestamp.desc()).limit(10)
        result = await self.db.execute(stmt)
        category_ids = list(set([row[0] for row in result.all()]))

        if not category_ids:
            return []

        rec_query = await self.db.execute(
            select(Product)
            .where(Product.category_id.in_(category_ids))
            .order_by(Product.views.desc())
            .limit(10)
        )
        return rec_query.scalars().all()
