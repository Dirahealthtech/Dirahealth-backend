from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Product, User, UserActivity


class UserActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def get_top_picks(self, user: User):
        # Get categories of products the user interacted with
        result = await self.db.execute(
            select(Product.category_id)
            .join(UserActivity, Product.id == UserActivity.product_id)
            .where(UserActivity.user_id == user.id)
            .order_by(UserActivity.timestamp.desc())
            .limit(10)
        )
        category_ids = list(set([row[0] for row in result.all()]))

        # Recommend popular products in those categories
        if category_ids:
            rec_query = await self.db.execute(
                select(Product)
                .where(Product.category_id.in_(category_ids))
                .order_by(Product.views.desc())
                .limit(10)
            )
            return rec_query.scalars().all()
        return []
