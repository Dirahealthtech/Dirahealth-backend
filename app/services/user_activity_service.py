from sqlalchemy import cast, desc, func, select, or_
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import String
from typing import List, Optional

from ..exceptions import NotFoundException
from ..models import OrderItem, Product, User, UserActivity, Category


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


    async def get_products(self, skip: int = 0, limit: int = 12, name: Optional[str] = None) -> List[Product]:
        stmt = (
            select(Product)
            .where(Product.is_active == True)
        )
        
        # Add name filter if provided
        if name:
            stmt = stmt.where(Product.name.ilike(f"%{name}%"))
        
        stmt = (
            stmt
            .offset(skip)
            .limit(limit)
            .order_by(desc(Product.created_at))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()


    async def get_product_by_slug(self, slug: str) -> Product:
        stmt = select(Product).where(Product.slug == slug, Product.is_active == True)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()
        
        if product is None:
            raise NotFoundException("Product not found!")
        
        return product


    async def get_recommended_products(self, product: Product, limit: int = 6) -> List[Product]:
        """
        Recommend products based on category and tag overlap.

        Sorted by:
        1. Estimated tag match score
        2. Popularity (number of OrderItems)
        """

        product_tags = product.tags or []

        # Start building the WHERE clause
        base_filters = [
            Product.is_active == True,
            Product.id != product.id,
        ]

        tag_filters = []
        for tag in product_tags:
            tag_filters.append(Product.tags.contains([tag]))

        stmt = (
            select(Product, func.count(OrderItem.id).label("popularity"))
            .outerjoin(OrderItem, Product.id == OrderItem.product_id)
            .where(
                *base_filters,
                or_(
                    Product.category_id == product.category_id,
                    *tag_filters
                )
            )
            .group_by(Product.id)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        # Score by number of overlapping tags (Python-side)
        def tag_match_score(p: Product) -> int:
            return len(set(p.tags or []) & set(product_tags))

        # Sort by tag match score then popularity (desc)
        sorted_products = sorted(
            rows,
            key=lambda row: (tag_match_score(row[0]), row[1]),  # row[0] is Product, row[1] is popularity
            reverse=True
        )

        # Return just the Product instances
        return [row[0] for row in sorted_products[:limit]]

