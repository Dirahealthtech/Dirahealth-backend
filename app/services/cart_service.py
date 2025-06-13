from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, delete
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..models import Cart, CartItem, CartServiceItem, Product, Service, User
from ..schemas.cart import CartItemCreate, CartServiceItemCreate, CartResponse
from ..exceptions import NotFoundException, BadRequestException

class CartService:
    async def get_or_create_cart(self, user_id: int, db: AsyncSession) -> Cart:
        """Get a user's cart or create one if it doesn't exist"""
        # Check if user has a cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            # Create a new cart
            cart = Cart(customer_id=user_id)
            db.add(cart)
            await db.commit()
            await db.refresh(cart)
            
        return cart
        
    async def add_product_to_cart(self, user_id: int, item_data: CartItemCreate, db: AsyncSession) -> CartItem:
        """Add a product to the cart"""
        # Get or create cart
        cart = await self.get_or_create_cart(user_id, db)
        
        # Check if product exists
        product = await db.get(Product, item_data.product_id)
        if not product:
            raise NotFoundException(f"Product with ID {item_data.product_id} not found")
            
        # Check if product is active
        if not product.is_active:
            raise BadRequestException("This product is not available")
            
        # Check if product is in stock
        if product.stock < item_data.quantity:
            raise BadRequestException(f"Not enough stock available. Only {product.stock} left")
        
        # Check if item already in cart
        query = select(CartItem).where(
            and_(
                CartItem.cart_id == cart.id,
                CartItem.product_id == item_data.product_id
            )
        )
        result = await db.execute(query)
        existing_item = result.scalars().first()
        
        if existing_item:
            # Update quantity
            existing_item.quantity += item_data.quantity
            await db.commit()
            await db.refresh(existing_item)
            
            # Update cart last_active
            cart.last_active = datetime.now()
            await db.commit()
            
            return existing_item
            
        # Add new item
        new_item = CartItem(
            cart_id=cart.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )
        db.add(new_item)
        
        # Update cart last_active
        cart.last_active = datetime.now()
        
        await db.commit()
        await db.refresh(new_item)
        
        return new_item
        
    async def add_service_to_cart(self, user_id: int, item_data: CartServiceItemCreate, db: AsyncSession) -> CartServiceItem:
        """Add a service to the cart"""
        # Get or create cart
        cart = await self.get_or_create_cart(user_id, db)
        
        # Check if service exists
        service = await db.get(Service, item_data.service_id)
        if not service:
            raise NotFoundException(f"Service with ID {item_data.service_id} not found")
            
        # Check if service is active
        if not service.is_active:
            raise BadRequestException("This service is not available")
        
        # Add service to cart
        new_item = CartServiceItem(
            cart_id=cart.id,
            service_id=item_data.service_id,
            appointment_details=item_data.appointment_details
        )
        db.add(new_item)
        
        # Update cart last_active
        cart.last_active = datetime.now()
        
        await db.commit()
        await db.refresh(new_item)
        
        return new_item

    async def remove_cart_item(self, user_id: int, item_id: int, db: AsyncSession) -> bool:
        """Remove a product item from cart"""
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Get the cart item
        item_query = select(CartItem).where(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalars().first()
        
        if not item:
            raise NotFoundException(f"Cart item with ID {item_id} not found")
        
        # Remove item
        await db.delete(item)
        
        # Update cart last_active
        cart.last_active = datetime.now()
        
        await db.commit()
        
        return True

    async def remove_cart_service_item(self, user_id: int, item_id: int, db: AsyncSession) -> bool:
        """Remove a service item from cart"""
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Get the cart service item
        item_query = select(CartServiceItem).where(
            and_(
                CartServiceItem.id == item_id,
                CartServiceItem.cart_id == cart.id
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalars().first()
        
        if not item:
            raise NotFoundException(f"Cart service item with ID {item_id} not found")
        
        # Remove item
        await db.delete(item)
        
        # Update cart last_active
        cart.last_active = datetime.now()
        
        await db.commit()
        
        return True

    async def update_cart_item_quantity(self, user_id: int, item_id: int, quantity: int, db: AsyncSession) -> CartItem:
        """Update the quantity of a cart item"""
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Get the cart item
        item_query = select(CartItem).where(
            and_(
                CartItem.id == item_id,
                CartItem.cart_id == cart.id
            )
        )
        item_result = await db.execute(item_query)
        item = item_result.scalars().first()
        
        if not item:
            raise NotFoundException(f"Cart item with ID {item_id} not found")
        
        # Check if product has enough stock
        product = await db.get(Product, item.product_id)
        if not product:
            raise NotFoundException(f"Product with ID {item.product_id} not found")
        
        if product.stock < quantity:
            raise BadRequestException(f"Not enough stock available. Only {product.stock} left")
        
        # Update quantity
        item.quantity = quantity
        
        # Update cart last_active
        cart.last_active = datetime.now()
        
        await db.commit()
        await db.refresh(item)
        
        return item

    async def clear_cart(self, user_id: int, db: AsyncSession) -> bool:
        """Remove all items from a user's cart"""
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Delete all cart items
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.execute(delete(CartServiceItem).where(CartServiceItem.cart_id == cart.id))
        
        # Reset discounts
        cart.applied_coupon_code = None
        cart.discount_amount = 0.0
        cart.discount_type = None
        cart.last_active = datetime.now()
        
        await db.commit()
        
        return True

    async def apply_coupon(self, user_id: int, coupon_code: str, db: AsyncSession) -> Cart:
        """Apply a coupon to the cart"""
        # Import Coupon model directly
        from ..models.coupon import Coupon  
        from datetime import datetime
        
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Get cart total before discount
        cart_total = await self.calculate_cart_total(cart.id, db)
        
        if cart_total <= 0:
            raise BadRequestException("Cannot apply coupon to an empty cart")
        
        # Find the coupon
        coupon_query = select(Coupon).where(
            and_(
                Coupon.code == coupon_code,
                Coupon.is_active == True,
                Coupon.valid_from <= datetime.now(),
                Coupon.valid_to >= datetime.now()
            )
        )
        coupon_result = await db.execute(coupon_query)
        coupon = coupon_result.scalars().first()
        
        if not coupon:
            raise NotFoundException(f"Coupon {coupon_code} not found or expired")
        
        # Check if coupon has reached usage limit
        if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
            raise BadRequestException("This coupon has reached its usage limit")
        
        # Check minimum order amount
        if coupon.minimum_order_amount and cart_total < coupon.minimum_order_amount:
            raise BadRequestException(f"Minimum order amount for this coupon is {coupon.minimum_order_amount}")
        
        # Calculate discount
        discount_amount = 0.0
        if coupon.discount_type == "percentage":
            discount_amount = cart_total * (coupon.discount_value / 100)
            # Apply maximum discount if set
            if coupon.maximum_discount and discount_amount > coupon.maximum_discount:
                discount_amount = coupon.maximum_discount
        else:  # fixed amount
            discount_amount = coupon.discount_value
            # Ensure discount doesn't exceed cart total
            if discount_amount > cart_total:
                discount_amount = cart_total
        
        # Apply discount to cart
        cart.applied_coupon_code = coupon.code
        cart.discount_amount = discount_amount
        cart.discount_type = coupon.discount_type
        cart.last_active = datetime.now()
        
        # Increment coupon usage
        coupon.times_used += 1
        
        await db.commit()
        await db.refresh(cart)
        
        return cart

    async def remove_coupon(self, user_id: int, db: AsyncSession) -> Cart:
        """Remove a coupon from the cart"""
        # Get user's cart
        query = select(Cart).where(Cart.customer_id == user_id)
        result = await db.execute(query)
        cart = result.scalars().first()
        
        if not cart:
            raise NotFoundException("Cart not found")
        
        # Remove coupon if applied
        if cart.applied_coupon_code:
            from ..models.coupon import Coupon
            
            # Decrement coupon usage
            coupon_query = select(Coupon).where(Coupon.code == cart.applied_coupon_code)
            coupon_result = await db.execute(coupon_query)
            coupon = coupon_result.scalars().first()
            
            if coupon:
                coupon.times_used -= 1
                if coupon.times_used < 0:
                    coupon.times_used = 0
        
        # Reset cart discount
        cart.applied_coupon_code = None
        cart.discount_amount = 0.0
        cart.discount_type = None
        cart.last_active = datetime.now()
        
        await db.commit()
        await db.refresh(cart)
        
        return cart

    async def calculate_cart_total(self, cart_id: int, db: AsyncSession) -> float:
        """Calculate the total value of items in cart"""
        # Get cart items
        items_query = select(CartItem).where(CartItem.cart_id == cart_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        # Get cart service items
        services_query = select(CartServiceItem).where(CartServiceItem.cart_id == cart_id)
        services_result = await db.execute(services_query)
        services = services_result.scalars().all()
        
        # Calculate products total
        product_total = 0.0
        for item in items:
            product = await db.get(Product, item.product_id)
            if product:
                # Use discounted price if available, otherwise use regular price
                price = product.discounted_price if hasattr(product, 'discounted_price') and product.discounted_price and product.discounted_price > 0 else product.price
                product_total += price * item.quantity
        
        # Calculate services total
        service_total = 0.0
        for service_item in services:
            service = await db.get(Service, service_item.service_id)
            if service:
                service_total += service.price
        
        # Return combined total
        return product_total + service_total

    async def get_cart_with_details(self, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get cart with detailed product and service information"""
        # Get cart
        cart = await self.get_or_create_cart(user_id, db)
        
        # Get cart items
        items_query = select(CartItem).where(CartItem.cart_id == cart.id)
        items_result = await db.execute(items_query)
        cart_items = items_result.scalars().all()
        
        items = []
        for item in cart_items:
            product = await db.get(Product, item.product_id)
            if product:
                # Get primary image URL
                image_url = None
                if hasattr(product, 'images') and product.images:
                    # Handle images based on how they're stored (could be JSON or relationship)
                    if isinstance(product.images, list):
                        # Find main image if images is a list of dictionaries
                        for img in product.images:
                            if isinstance(img, dict) and img.get("isMain", False):
                                image_url = img.get("url")
                                break
                        
                        # If no main image found, use the first one
                        if not image_url and product.images and isinstance(product.images[0], dict):
                            image_url = product.images[0].get("url")
                
                # Use discounted price if available
                price = product.discounted_price if hasattr(product, 'discounted_price') and product.discounted_price and product.discounted_price > 0 else product.price
                
                items.append({
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "added_at": item.created_at,
                    "product_name": product.name,
                    "product_price": price,
                    "product_image": image_url
                })
        
        # Get cart service items
        services_query = select(CartServiceItem).where(CartServiceItem.cart_id == cart.id)
        services_result = await db.execute(services_query)
        cart_services = services_result.scalars().all()
        
        service_items = []
        for item in cart_services:
            service = await db.get(Service, item.service_id)
            if service:
                service_items.append({
                    "id": item.id,
                    "cart_id": item.cart_id,
                    "service_id": item.service_id,
                    "appointment_details": item.appointment_details,
                    "service_name": service.name,
                    "service_price": service.price
                })
        
        # Calculate subtotal
        subtotal = await self.calculate_cart_total(cart.id, db)
        
        # Get discount
        discount = cart.discount_amount or 0.0
        
        # Calculate total
        total = max(0, subtotal - discount)
        
        return {
            "id": cart.id,
            "customer_id": cart.customer_id,
            "applied_coupon_code": cart.applied_coupon_code,
            "discount_amount": cart.discount_amount or 0.0,
            "discount_type": cart.discount_type,
            "last_active": cart.last_active or cart.created_at,
            "items": items,
            "service_items": service_items,
            "subtotal": subtotal,
            "discount": discount,
            "total": total
        }