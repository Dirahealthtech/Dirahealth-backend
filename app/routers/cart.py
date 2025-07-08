from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_db, get_current_user
from ..models import User, Cart, CartItem, CartServiceItem, Product, Service
from ..schemas.cart import CartItemCreate, CartServiceItemCreate, CartResponse
from ..services.cart_service import CartService

router = APIRouter()
cart_service = CartService()

@router.get("/", response_model=CartResponse)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's cart with details"""
    return await cart_service.get_cart_with_details(current_user.id, db)

@router.post("/items")
async def add_product_to_cart(
    item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a product to the cart"""
    return await cart_service.add_product_to_cart(current_user.id, item, db)

@router.post("/services")
async def add_service_to_cart(
    item: CartServiceItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a service to the cart"""
    return await cart_service.add_service_to_cart(current_user.id, item, db)

@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove an item from the cart"""
    return await cart_service.remove_cart_item(current_user.id, item_id, db)

@router.delete("/services/{item_id}")
async def remove_cart_service_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a service from the cart"""
    return await cart_service.remove_cart_service_item(current_user.id, item_id, db)

@router.post("/apply-coupon/{coupon_code}")
async def apply_coupon(
    coupon_code: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply a coupon to the cart"""
    return await cart_service.apply_coupon(current_user.id, coupon_code, db)

@router.put("/items/{item_id}")
async def update_cart_item_quantity(
    item_id: int,
    quantity: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update quantity of a cart item"""
    return await cart_service.update_cart_item_quantity(current_user.id, item_id, quantity, db)

@router.delete("/coupon")
async def remove_coupon(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove coupon from cart"""
    return await cart_service.remove_coupon(current_user.id, db)

@router.delete("/")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clear all items from cart"""
    return await cart_service.clear_cart(current_user.id, db)