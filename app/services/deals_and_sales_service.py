from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.flash_sales import FlashSale


class ProductDealsandSalesService:
    def __init__(self, db):
        self.db = db


    async def get_active_flash_sales(self):
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(FlashSale)
            .where(FlashSale.start_time <= now, FlashSale.end_time >= now)
            .options(selectinload(FlashSale.products))
        )
        return result.scalars().all()

