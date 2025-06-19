from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_db
from ..schemas.sales_schema import FlashSalesSchemaResponse
from ..services.deals_and_sales_service import ProductDealsandSalesService


router = APIRouter()


async def get_product_deals_and_sales_service(db: AsyncSession = Depends(get_db)) -> ProductDealsandSalesService:
    return ProductDealsandSalesService(db)


@router.get("/flash-sales", response_model=List[FlashSalesSchemaResponse])
async def get_active_flash_sales(
    service: ProductDealsandSalesService = Depends(get_product_deals_and_sales_service),

):
    """
    Retrieve all currently active flash sales.
    This endpoint fetches and returns a list of active flash sales from the product deals and sales service.
    It uses dependency injection to access the service, which handles the business logic and database interactions.

    Args:
        service (ProductDealsandSalesService): The service used to interact with product deals and sales.
            Injected automatically via FastAPI's dependency injection.
    Returns:
        List[FlashSale]: A list of active flash sale objects.
    Raises:
        HTTPException: If there is an error retrieving the flash sales.
    """

    return await service.get_active_flash_sales()
