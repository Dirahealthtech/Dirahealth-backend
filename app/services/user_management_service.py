from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, desc, and_, or_
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import math

from ..models.user import User
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.review import Review
from ..models.customer_profile import CustomerProfile
from ..enums import UserRole, OrderStatus, PaymentStatus
from ..exceptions import NotFoundException, BadRequestException
from ..schemas.user_management import (
    UserSummaryResponse, 
    UserDetailResponse, 
    UserListResponse,
    UserSearchFilters,
    UserStatsResponse,
    OrderSummaryResponse
)


class UserManagementService:
    
    async def get_all_users(
        self, 
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        filters: Optional[UserSearchFilters] = None
    ) -> UserListResponse:
        """Get paginated list of all users with summary information"""
        
        # Base query
        query = select(User).options(
            selectinload(User.orders),
            selectinload(User.customer_profile)
        )
        
        # Apply search filter
        if search:
            search_filter = or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.phone_number.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        
        # Apply filters
        if filters:
            if filters.role:
                query = query.where(User.role == filters.role)
            if filters.is_verified is not None:
                query = query.where(User.is_verified == filters.is_verified)
            if filters.created_after:
                query = query.where(User.created_at >= filters.created_after)
            if filters.created_before:
                query = query.where(User.created_at <= filters.created_before)
        
        # Get total count
        count_query = select(func.count()).select_from(User)
        if search:
            count_query = count_query.where(search_filter)
        if filters:
            if filters.role:
                count_query = count_query.where(User.role == filters.role)
            if filters.is_verified is not None:
                count_query = count_query.where(User.is_verified == filters.is_verified)
            if filters.created_after:
                count_query = count_query.where(User.created_at >= filters.created_after)
            if filters.created_before:
                count_query = count_query.where(User.created_at <= filters.created_before)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(desc(User.created_at))
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Convert to response format with statistics
        user_summaries = []
        for user in users:
            # Calculate user statistics
            total_orders = len(user.orders) if user.orders else 0
            total_spent = sum(order.total for order in user.orders) if user.orders else 0.0
            last_order_date = max(order.created_at for order in user.orders) if user.orders else None
            
            user_summary = UserSummaryResponse(
                id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                phone_number=user.phone_number,
                role=user.role,
                is_verified=user.is_verified,
                created_at=user.created_at,
                updated_at=user.updated_at,
                total_orders=total_orders,
                total_spent=total_spent,
                last_order_date=last_order_date
            )
            user_summaries.append(user_summary)
        
        pages = math.ceil(total / limit) if limit > 0 else 1
        page = (skip // limit) + 1 if limit > 0 else 1
        
        return UserListResponse(
            users=user_summaries,
            total=total,
            page=page,
            per_page=limit,
            pages=pages
        )
    
    async def get_user_detail(self, user_id: int, db: AsyncSession) -> UserDetailResponse:
        """Get detailed information about a specific user"""
        
        # Get user with all related data
        query = select(User).options(
            selectinload(User.orders).selectinload(Order.items),
            selectinload(User.customer_profile),
            selectinload(User.reviews)
        ).where(User.id == user_id)
        
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        # Calculate statistics
        total_orders = len(user.orders) if user.orders else 0
        total_spent = sum(order.total for order in user.orders) if user.orders else 0.0
        last_order_date = max(order.created_at for order in user.orders) if user.orders else None
        
        # Get recent orders (last 10)
        recent_orders = []
        if user.orders:
            sorted_orders = sorted(user.orders, key=lambda x: x.created_at, reverse=True)[:10]
            for order in sorted_orders:
                items_count = len(order.items) if order.items else 0
                recent_orders.append(OrderSummaryResponse(
                    id=order.id,
                    order_number=order.order_number,
                    status=order.status,
                    total=order.total,
                    payment_status=order.payment_status.value,
                    created_at=order.created_at,
                    items_count=items_count
                ))
        
        # Get shipping addresses from customer profile
        shipping_addresses = []
        if user.customer_profile and hasattr(user.customer_profile, 'shipping_addresses'):
            shipping_addresses = user.customer_profile.shipping_addresses or []
        
        return UserDetailResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=user.phone_number,
            role=user.role,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            total_orders=total_orders,
            total_spent=total_spent,
            last_order_date=last_order_date,
            customer_profile=user.customer_profile.__dict__ if user.customer_profile else None,
            recent_orders=recent_orders,
            total_reviews=len(user.reviews) if user.reviews else 0,
            account_created=user.created_at,
            shipping_addresses=shipping_addresses
        )
    
    async def get_user_orders(
        self, 
        user_id: int, 
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20
    ) -> List[OrderSummaryResponse]:
        """Get all orders for a specific user"""
        
        # Check if user exists
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        # Get user's orders
        query = select(Order).options(
            selectinload(Order.items)
        ).where(Order.customer_id == user_id).order_by(desc(Order.created_at)).offset(skip).limit(limit)
        
        result = await db.execute(query)
        orders = result.scalars().all()
        
        order_summaries = []
        for order in orders:
            items_count = len(order.items) if order.items else 0
            order_summaries.append(OrderSummaryResponse(
                id=order.id,
                order_number=order.order_number,
                status=order.status,
                total=order.total,
                payment_status=order.payment_status.value,
                created_at=order.created_at,
                items_count=items_count
            ))
        
        return order_summaries
    
    async def ban_user(self, user_id: int, reason: str, db: AsyncSession) -> dict:
        """Ban a user account"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        if user.role == UserRole.ADMIN:
            raise BadRequestException("Cannot ban admin users")
        
        # For now, we'll use is_verified as a ban flag (you might want to add a dedicated ban field)
        user.is_verified = False
        
        await db.commit()
        await db.refresh(user)
        
        return {"message": f"User {user.email} has been banned", "reason": reason}
    
    async def unban_user(self, user_id: int, db: AsyncSession) -> dict:
        """Unban a user account"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        user.is_verified = True
        
        await db.commit()
        await db.refresh(user)
        
        return {"message": f"User {user.email} has been unbanned"}
    
    async def delete_user(self, user_id: int, db: AsyncSession) -> dict:
        """Delete a user account (soft delete or hard delete based on business rules)"""
        
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException(f"User with id {user_id} not found")
        
        if user.role == UserRole.ADMIN:
            raise BadRequestException("Cannot delete admin users")
        
        # Check if user has orders - might want to prevent deletion
        orders_query = select(func.count()).select_from(Order).where(Order.customer_id == user_id)
        orders_result = await db.execute(orders_query)
        orders_count = orders_result.scalar()
        
        if orders_count > 0:
            raise BadRequestException(f"Cannot delete user with existing orders. User has {orders_count} orders.")
        
        await db.delete(user)
        await db.commit()
        
        return {"message": f"User account {user.email} has been deleted"}
    
    async def get_user_statistics(self, db: AsyncSession) -> UserStatsResponse:
        """Get overall user statistics for admin dashboard"""
        
        # Total users
        total_users_query = select(func.count()).select_from(User)
        total_users_result = await db.execute(total_users_query)
        total_users = total_users_result.scalar()
        
        # Active users (verified)
        active_users_query = select(func.count()).select_from(User).where(User.is_verified == True)
        active_users_result = await db.execute(active_users_query)
        active_users = active_users_result.scalar()
        
        # Banned users (unverified)
        banned_users = total_users - active_users
        
        # Verified vs unverified
        verified_users = active_users
        unverified_users = banned_users
        
        # Users with orders
        users_with_orders_query = select(func.count(func.distinct(Order.customer_id))).select_from(Order)
        users_with_orders_result = await db.execute(users_with_orders_query)
        users_with_orders = users_with_orders_result.scalar() or 0
        
        # Total revenue
        total_revenue_query = select(func.sum(Order.total)).select_from(Order).where(Order.status == OrderStatus.DELIVERED)
        total_revenue_result = await db.execute(total_revenue_query)
        total_revenue = total_revenue_result.scalar() or 0.0
        
        # Average order value
        avg_order_query = select(func.avg(Order.total)).select_from(Order).where(Order.status == OrderStatus.DELIVERED)
        avg_order_result = await db.execute(avg_order_query)
        avg_order_value = avg_order_result.scalar() or 0.0
        
        # Registration trend (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        registration_trend = {}
        
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            count_query = select(func.count()).select_from(User).where(
                and_(User.created_at >= date_start, User.created_at < date_end)
            )
            count_result = await db.execute(count_query)
            count = count_result.scalar()
            
            registration_trend[date.strftime('%Y-%m-%d')] = count
        
        return UserStatsResponse(
            total_users=total_users,
            active_users=active_users,
            banned_users=banned_users,
            verified_users=verified_users,
            unverified_users=unverified_users,
            users_with_orders=users_with_orders,
            total_revenue=float(total_revenue),
            avg_order_value=float(avg_order_value),
            registration_trend=registration_trend
        )


# Create singleton instance
user_management_service = UserManagementService()
