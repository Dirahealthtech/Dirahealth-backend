from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_current_user, get_db
from ..models import User
from ..schemas.product import ProductResponse
from ..services.user_activity_service import UserActivityService

router = APIRouter()


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
    current_user: User = Depends(get_current_user),
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
    return await service.get_top_picks(current_user)
