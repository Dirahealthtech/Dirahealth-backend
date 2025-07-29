from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..core.dependencies import get_anonymous_user, get_db
from ..models import User
from ..schemas.product import ProductResponse
from ..schemas.category import CategoryResponse
from ..services.user_activity_service import UserActivityService
from ..exceptions import NotFoundException


router = APIRouter(prefix='/activity')


async def get_user_activity_service(db: AsyncSession = Depends(get_db)) -> UserActivityService:
    """
    Dependency function that provides an instance of UserActivityService.

    Args:
        db (AsyncSession): The asynchronous database session dependency.

    Returns:
        UserActivityService: An instance of the UserActivityService initialized with the provided database session.
    """

    return UserActivityService(db)


@router.get("/top-picks", response_model=List[ProductResponse])
async def get_top_picks(
    current_user: Optional[User] = Depends(get_anonymous_user),
    anonymous_user: Optional[str] = Query(None),
    service: UserActivityService = Depends(get_user_activity_service),
):
    """
    Retrieve the top picks for the current user.
    This endpoint returns a list of recommended items or activities for the authenticated user,
    based on their activity history or preferences.

    Args:
        current_user (User): The currently authenticated user, injected by dependency.
        service (UserActivityService): The user activity service, injected by dependency.

    Returns:
        List[Any]: A list of top picks or recommendations for the user.

    Raises:
        HTTPException: If the user is not authenticated or an error occurs during retrieval.
    """
    return await service.get_top_picks(current_user, anonymous_user)


@router.get('/homepage', response_model=List[ProductResponse])
async def get_products(service: UserActivityService = Depends(get_user_activity_service)):
    """
    Retrieve available products to users. This endpoint returns a list of products sold by suppliers
    via the website.
    """
    return await service.get_products()

@router.get('/product/{slug}', response_model=ProductResponse)
async def get_product_details_by_slug(
    slug: str,
    service: UserActivityService = Depends(get_user_activity_service),
):
    try:
        result  = await service.get_product_by_slug(slug)
        return result
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise e


@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    service: UserActivityService = Depends(get_user_activity_service),
    skip: int = 0,
    limit: int = 100
):
    """
    **List All Categories**
    
    Retrieves a paginated list of all product categories.
    
    **Query Parameters:**

    - **skip**: Number of categories to skip (for pagination) - Default: 0
    - **limit**: Maximum number of categories to return - Default: 100, Max: 100
    """
    categories = await service.get_product_categories(skip, limit)
    return categories
