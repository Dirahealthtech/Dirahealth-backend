from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_db, get_current_user, get_current_admin
from ..models import User
from ..schemas.order import OrderCreate, OrderResponse, OrderDetail, OrderStatusUpdate
from ..services.order_service import OrderService
from ..models.order import OrderStatus
from ..schemas.tracking import TrackingUpdate, TrackingResponse

router = APIRouter()
order_service = OrderService()

@router.post("/", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new order from cart"""
    return await order_service.create_order_from_cart(current_user.id, order_data, db, background_tasks)

@router.get("/", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 10
):
    """Get all orders for the current user"""
    return await order_service.get_user_orders(current_user.id, db, skip, limit)

@router.get("/{order_id}", response_model=OrderDetail)
async def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about an order"""
    return await order_service.get_order_detail(order_id, current_user.id, db)

@router.post("/{order_id}/delivery-confirmation")
async def confirm_delivery(
    order_id: int,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Mark an order as delivered and complete the cash on delivery payment"""
    return await order_service.update_order_status(
        order_id=order_id,
        status=OrderStatus.DELIVERED,
        admin_id=admin_user.id,
        db=db,
        notes="Delivery confirmed. Payment collected."
    )

@router.get("/{order_id}/tracking", response_model=TrackingResponse)
async def get_order_tracking(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get tracking information for an order"""
    return await order_service.get_tracking_info(order_id, current_user.id, db)

@router.patch("/{order_id}/tracking", response_model=TrackingResponse)
async def update_order_tracking(
    order_id: int,
    tracking_data: TrackingUpdate,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update tracking information for an order (admin only)"""
    return await order_service.update_tracking_info(
        order_id=order_id,
        admin_id=admin_user.id,
        tracking_data=tracking_data.dict(),
        db=db
    )

@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an order's status (admin only)"""
    return await order_service.update_order_status(
        order_id=order_id,
        status=status_update.status,
        admin_id=admin_user.id,
        db=db,
        notes=status_update.notes,
        background_tasks=background_tasks
    )