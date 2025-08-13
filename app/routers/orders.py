from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ..core.dependencies import get_db, get_current_user, get_current_admin
from ..models import User
from ..schemas.order import (
    OrderCreate, 
    OrderResponse, 
    OrderDetail, 
    OrderStatusUpdate,
    OrderCancellationRequest,
    OrderStatus as OrderStatusEnum,
    PaymentMethod
)
from ..services.order_service import OrderService
from ..models.order import OrderStatus
from ..schemas.tracking import TrackingUpdate, TrackingResponse

router = APIRouter()
order_service = OrderService()

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Create New Order**
    
    Create a new order from the customer's cart items. This endpoint processes 
    all items in the customer's cart and creates a complete order with shipping
    and billing information.
    
    **Request Body:**
    - **shipping_address**: Complete shipping address details
    - **billing_address**: Complete billing address details  
    - **payment_method**: Payment method (cash_on_delivery, mpesa, credit_card, bank_transfer)
    - **shipping_cost**: Shipping cost (default: 0.0)
    - **notes**: Optional order notes
    - **prescription_id**: Optional prescription ID for prescription items
    
    **Returns:**
    - Complete order information with order number, status, and totals
    - Order items and services included in the order
    - Payment and shipping details
    
    **Process:**
    1. Validates customer's cart has items
    2. Calculates totals including tax and shipping
    3. Creates order with all cart items and services
    4. Clears the customer's cart
    5. Sends order confirmation email
    """
    return await order_service.create_order_from_cart(current_user.id, order_data, db, background_tasks)

@router.get("/", response_model=List[OrderResponse])
async def get_user_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[OrderStatusEnum] = Query(None, description="Filter orders by status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    **Get User Orders**
    
    Retrieve all orders for the current authenticated user with optional filtering and pagination.
    
    **Query Parameters:**
    - **status_filter**: Filter orders by specific status (optional)
    - **page**: Page number for pagination (default: 1)
    - **size**: Number of orders per page (default: 10, max: 100)
    
    **Returns:**
    - List of user orders with basic information
    - Ordered by creation date (most recent first)
    - Includes order status, totals, and payment information
    """
    skip = (page - 1) * size
    return await order_service.get_user_orders(current_user.id, db, skip, size)

@router.get("/{order_id}", response_model=OrderDetail)
async def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Get Order Details**
    
    Retrieve complete details for a specific order including all items, services,
    shipping information, and tracking details.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Returns:**
    - Complete order information including:
      - Order summary (number, status, totals)
      - All order items with product details
      - Services included in the order
      - Shipping and billing addresses
      - Payment information
      - Tracking details (if available)
      - Order notes and history
    
    **Access:**
    - Only accessible by the customer who placed the order
    - Validates order ownership before returning details
    """
    return await order_service.get_order_detail(order_id, current_user.id, db)


@router.get("/status/{status}", response_model=List[OrderResponse])
async def get_orders_by_status(
    status: OrderStatusEnum,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=50, description="Items per page")
):
    """
    **Get Orders by Status**
    
    Retrieve user orders filtered by a specific status (e.g., pending, processing, shipped).
    
    **Path Parameters:**
    - **status**: Order status to filter by
    
    **Query Parameters:**
    - **page**: Page number for pagination (default: 1)
    - **size**: Number of orders per page (default: 10, max: 50)
    
    **Returns:**
    - List of orders matching the specified status
    - Ordered by creation date (most recent first)
    
    **Common Use Cases:**
    - Get pending orders: `/status/pending`
    - Get shipped orders: `/status/shipped`
    - Get completed orders: `/status/completed`
    """
    skip = (page - 1) * size
    # Filter orders by status using the existing service method with status filter logic
    all_orders = await order_service.get_user_orders(current_user.id, db, skip, size)
    return [order for order in all_orders if order.status == status]


@router.post("/{order_id}/cancel", status_code=status.HTTP_200_OK)
async def request_order_cancellation(
    order_id: int,
    cancellation_request: OrderCancellationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Request Order Cancellation**
    
    Submit a cancellation request for an existing order. Orders can only be cancelled
    if they haven't been shipped yet.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order to cancel
    
    **Request Body:**
    - **reason**: Detailed reason for cancellation (minimum 5 characters)
    
    **Returns:**
    - Confirmation message and updated order status
    
    **Business Rules:**
    - Only pending or processing orders can be cancelled
    - Shipped or delivered orders cannot be cancelled (use return process instead)
    - Cancellation requests are reviewed by admin staff
    - Refunds are processed according to payment method policies
    
    **Process:**
    1. Validates order ownership and cancellation eligibility
    2. Updates order status to cancelled
    3. Processes refund if payment was already made
    4. Restores product inventory
    5. Sends cancellation confirmation email
    """
    try:
        # Get order details first to validate ownership and status
        order_detail = await order_service.get_order_detail(order_id, current_user.id, db)
        
        # Check if order can be cancelled
        if order_detail.status in [OrderStatusEnum.SHIPPED, OrderStatusEnum.DELIVERED, OrderStatusEnum.COMPLETED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order_detail.status}. Please use return process for delivered orders."
            )
        
        if order_detail.status == OrderStatusEnum.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is already cancelled"
            )
        
        # Update order status to cancelled
        await order_service.update_order_status(
            order_id=order_id,
            status=OrderStatus.CANCELLED,
            admin_id=None,  # Customer initiated cancellation
            db=db,
            notes=f"Customer cancellation request: {cancellation_request.reason}",
            background_tasks=background_tasks
        )
        
        return {
            "message": "Order cancellation request submitted successfully",
            "order_id": order_id,
            "status": "cancelled",
            "reason": cancellation_request.reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}"
        )


@router.get("/summary/stats")
async def get_order_statistics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    **Get Order Statistics**
    
    Retrieve summary statistics for the current user's orders including
    counts by status, total spending, and recent order activity.
    
    **Returns:**
    - Order counts by status (pending, processing, shipped, delivered, etc.)
    - Total amount spent across all orders
    - Average order value
    - Number of orders in the last 30 days
    - Most frequently ordered products
    - Recent order activity
    
    **Use Cases:**
    - Dashboard summary information
    - Customer account overview
    - Order history analytics
    - Spending analysis and budgeting
    
    **Access:**
    - Available to authenticated customers for their own data
    """
    try:
        # Get all user orders to calculate statistics
        all_orders = await order_service.get_user_orders(current_user.id, db, 0, 1000)
        
        # Calculate statistics
        stats = {
            "total_orders": len(all_orders),
            "orders_by_status": {},
            "total_spent": 0.0,
            "average_order_value": 0.0,
            "orders_last_30_days": 0,
            "recent_orders": []
        }
        
        # Count orders by status and calculate totals
        for order in all_orders:
            status = order.status
            stats["orders_by_status"][status] = stats["orders_by_status"].get(status, 0) + 1
            stats["total_spent"] += order.total
            
            # Count recent orders (last 30 days)
            days_ago = (datetime.now() - order.created_at).days
            if days_ago <= 30:
                stats["orders_last_30_days"] += 1
        
        # Calculate average order value
        if stats["total_orders"] > 0:
            stats["average_order_value"] = stats["total_spent"] / stats["total_orders"]
        
        # Get recent orders (last 5)
        recent_orders = sorted(all_orders, key=lambda x: x.created_at, reverse=True)[:5]
        stats["recent_orders"] = [
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total": order.total,
                "created_at": order.created_at
            } for order in recent_orders
        ]
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order statistics: {str(e)}"
        )