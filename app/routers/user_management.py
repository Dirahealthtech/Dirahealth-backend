from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ..core.dependencies import get_db, RoleChecker
from ..enums import UserRole
from ..schemas.user_management import (
    UserListResponse,
    UserDetailResponse,
    UserSummaryResponse,
    OrderSummaryResponse,
    UserActionRequest,
    BanUserRequest,
    UserSearchFilters,
    UserStatsResponse
)
from ..services.user_management_service import user_management_service
from ..exceptions import NotFoundException, BadRequestException

router = APIRouter(prefix="/admin/users", tags=["User Management"])

admin_only = Depends(RoleChecker([UserRole.ADMIN]))


@router.get("/", response_model=UserListResponse)
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    search: Optional[str] = Query(None, description="Search by name, email, or phone"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    created_after: Optional[datetime] = Query(None, description="Filter users created after this date"),
    created_before: Optional[datetime] = Query(None, description="Filter users created before this date"),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get All Users - Admin Only**
    
    Retrieve a paginated list of all users with summary information including:
    - Basic user information (name, email, phone, role)
    - Account status and verification
    - Order statistics (total orders, amount spent)
    - Registration date and last activity
    
    **Query Parameters:**
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return (1-100)
    - **search**: Search term for name, email, or phone number
    - **role**: Filter by specific user role (CUSTOMER, ADMIN, etc.)
    - **is_verified**: Filter by account verification status
    - **created_after**: Show only users registered after this date
    - **created_before**: Show only users registered before this date
    
    **Returns:** Paginated list with user summaries and pagination metadata
    """
    try:
        filters = UserSearchFilters(
            role=role,
            is_verified=is_verified,
            created_after=created_after,
            created_before=created_before
        )
        
        result = await user_management_service.get_all_users(
            db=db,
            skip=skip,
            limit=limit,
            search=search,
            filters=filters
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get User Statistics - Admin Only**
    
    Retrieve comprehensive statistics about the user base including:
    - Total user counts by status and role
    - Revenue metrics and order statistics
    - Registration trends over the last 30 days
    - User activity and engagement metrics
    
    **Returns:** Complete user statistics for admin dashboard
    """
    try:
        stats = await user_management_service.get_user_statistics(db)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user statistics: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get User Details - Admin Only**
    
    Retrieve comprehensive information about a specific user including:
    - Complete user profile and contact information
    - Account status, verification, and role details
    - Order history and transaction summary
    - Customer profile and shipping addresses
    - Review activity and engagement metrics
    
    **Path Parameters:**
    - **user_id**: The ID of the user to retrieve
    
    **Returns:** Complete user profile with all related information
    """
    try:
        user_detail = await user_management_service.get_user_detail(user_id, db)
        return user_detail
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user details: {str(e)}"
        )


@router.get("/{user_id}/orders", response_model=List[OrderSummaryResponse])
async def get_user_orders(
    user_id: int,
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of orders to return"),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get User Orders - Admin Only**
    
    Retrieve all orders placed by a specific user with detailed information:
    - Order numbers and current status
    - Payment information and transaction details
    - Order totals and item counts
    - Creation and delivery dates
    
    **Path Parameters:**
    - **user_id**: The ID of the user whose orders to retrieve
    
    **Query Parameters:**
    - **skip**: Number of orders to skip for pagination
    - **limit**: Maximum number of orders to return (1-100)
    
    **Returns:** List of order summaries for the specified user
    """
    try:
        orders = await user_management_service.get_user_orders(
            user_id=user_id,
            db=db,
            skip=skip,
            limit=limit
        )
        return orders
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user orders: {str(e)}"
        )


@router.post("/{user_id}/ban", status_code=status.HTTP_200_OK)
async def ban_user(
    user_id: int,
    ban_request: BanUserRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Ban User Account - Admin Only**
    
    Ban a user account, preventing them from accessing the system:
    - Immediately revokes access to the platform
    - Maintains order history and data integrity
    - Records the ban reason for administrative purposes
    - Cannot be used on admin accounts for security
    
    **Path Parameters:**
    - **user_id**: The ID of the user to ban
    
    **Request Body:**
    - **reason**: Reason for banning the user (optional but recommended)
    - **ban_duration_days**: Duration of ban in days (optional, permanent if not specified)
    
    **Returns:** Confirmation message with ban details
    """
    try:
        result = await user_management_service.ban_user(
            user_id=user_id,
            reason=ban_request.reason or "No reason provided",
            db=db
        )
        return result
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ban user: {str(e)}"
        )


@router.post("/{user_id}/unban", status_code=status.HTTP_200_OK)
async def unban_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Unban User Account - Admin Only**
    
    Remove ban from a user account, restoring their access:
    - Restores full platform access
    - Maintains all previous data and order history
    - User can immediately log in and use the platform
    
    **Path Parameters:**
    - **user_id**: The ID of the user to unban
    
    **Returns:** Confirmation message
    """
    try:
        result = await user_management_service.unban_user(user_id, db)
        return result
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unban user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Delete User Account - Admin Only**
    
    **⚠️DANGER: This permanently deletes a user account**
    
    Completely remove a user account from the system:
    - **Permanently deletes** all user data
    - **Cannot be undone** - use with extreme caution
    - Blocked if user has existing orders (data integrity)
    - Cannot be used on admin accounts for security
    - Consider banning instead of deletion in most cases
    
    **Path Parameters:**
    - **user_id**: The ID of the user to delete
    
    **Returns:** Confirmation message
    
    **Notes:**
    - Users with orders cannot be deleted to maintain order history
    - Consider using the ban feature instead for reversible actions
    - This action is logged for administrative audit purposes
    """
    try:
        result = await user_management_service.delete_user(user_id, db)
        return result
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BadRequestException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )
