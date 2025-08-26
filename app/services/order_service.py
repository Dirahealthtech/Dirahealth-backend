import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, delete

from ..models import Cart, CartItem, CartServiceItem, Order, OrderItem, OrderService as OrderServiceModel
from ..models import OrderStatusHistory
from ..models import PaymentTransaction
from ..models import OrderCancellation
from ..models import Refund
from ..models import Product, Service, User, Appointment
from ..models.shipment_tracking import ShipmentTracking
from ..models.shipment_checkpoint import ShipmentCheckpoint
from ..schemas.order import OrderCreate, OrderResponse
from ..enums import OrderStatus, PaymentMethod, PaymentStatus
from ..exceptions import NotFoundException, BadRequestException
from ..services.email_service import EmailService
from ..core.config import Config
from ..core.dependencies import get_db


class OrderService:
    def _convert_to_naive_datetime(self, dt: datetime) -> datetime:
        """Convert timezone-aware datetime to timezone-naive datetime"""
        if dt is None:
            return None
        if dt.tzinfo is not None:
            # Convert to naive datetime by removing timezone info
            return dt.replace(tzinfo=None)
        return dt

    async def _get_user_by_id(self, user_id: int, db: AsyncSession) -> User:
        """Get user by ID"""
        user = await db.get(User, user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")
        return user

    async def create_order_from_cart(
        self,
        user_id: int,
        order_data: OrderCreate,
        db: AsyncSession,
        background_tasks: BackgroundTasks
    ) -> Order:
        """Create a new order from the user's cart"""
        try:
            # Get user's cart
            query = select(Cart).where(Cart.customer_id == user_id)
            result = await db.execute(query)
            cart = result.scalars().first()
            
            if not cart:
                raise NotFoundException("Shopping cart not found")
                
            # Check if cart is empty
            cart_items_query = select(CartItem).where(CartItem.cart_id == cart.id)
            cart_items_result = await db.execute(cart_items_query)
            cart_items = cart_items_result.scalars().all()
            
            cart_services_query = select(CartServiceItem).where(CartServiceItem.cart_id == cart.id)
            cart_services_result = await db.execute(cart_services_query)
            cart_services = cart_services_result.scalars().all()
            
            if not cart_items and not cart_services:
                raise BadRequestException("Your cart is empty")
                
            # Calculate order totals
            subtotal = 0.0
            tax = 0.0
            
            # Calculate product subtotal
            for item in cart_items:
                product = await db.get(Product, item.product_id)
                if not product:
                    raise NotFoundException(f"Product with ID {item.product_id} not found")
                    
                # Check stock
                if product.stock < item.quantity:
                    raise BadRequestException(f"Not enough stock for {product.name}. Only {product.stock} available")
                    
                # Add to subtotal
                subtotal += product.price * item.quantity
                # Calculate tax
                tax += (product.price * item.quantity * product.tax_rate / 100)
                
            # Calculate service subtotal
            for service_item in cart_services:
                service = await db.get(Service, service_item.service_id)
                if not service:
                    raise NotFoundException(f"Service with ID {service_item.service_id} not found")
                    
                # Add to subtotal
                subtotal += service.price
                
            # Apply discount from cart if any
            discount = cart.discount_amount if cart.discount_amount else 0.0
            
            # Calculate shipping based on order_data
            shipping_cost = order_data.shipping_cost
            
            # Calculate total
            total = subtotal + tax + shipping_cost - discount
            
            # Create order
            new_order = Order(
                order_number=f"ORDER-{uuid.uuid4().hex[:8].upper()}",
                customer_id=user_id,
                status=OrderStatus.PROCESSING if order_data.payment_method == PaymentMethod.CASH_ON_DELIVERY else OrderStatus.PENDING,
                shipping_address=order_data.shipping_address,
                billing_address=order_data.billing_address,
                payment_method=order_data.payment_method,
                payment_status=PaymentStatus.PENDING,
                payment_amount=total,
                payment_currency="KES",  # Adjust as needed
                subtotal=subtotal,
                tax=tax,
                shipping_cost=shipping_cost,
                discount=discount,
                total=total,
                notes=order_data.notes,
                prescription_id=order_data.prescription_id,
                requires_verification=any(getattr(item.product, 'requires_prescription', False) for item in cart_items)
            )
            
            db.add(new_order)
            await db.flush()  # Get the order ID without committing
            
            # Create order items
            for item in cart_items:
                product = await db.get(Product, item.product_id)
                
                # Create order item
                order_item = OrderItem(
                    order_id=new_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=product.price,
                    discount=0  # Could calculate individual discounts if needed
                )
                db.add(order_item)
                
                # Update product stock
                product.stock -= item.quantity
                
            # Create order services
            for service_item in cart_services:
                service = await db.get(Service, service_item.service_id)
                
                # Create appointment if details provided
                appointment_id = None
                if service_item.appointment_details:
                    # Create appointment logic would go here
                    # This is simplified
                    appointment = Appointment(
                        service_id=service_item.service_id,
                        customer_id=user_id,
                        # Map other appointment details
                    )
                    db.add(appointment)
                    await db.flush()
                    appointment_id = appointment.id
                    
                # Create order service
                order_service_entry = OrderServiceModel(
                    order_id=new_order.id,
                    service_id=service_item.service_id,
                    price=service.price,
                    appointment_id=appointment_id
                )
                db.add(order_service_entry)
                
            # Clear the cart
            await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
            await db.execute(delete(CartServiceItem).where(CartServiceItem.cart_id == cart.id))
            
            # Reset cart discounts
            cart.applied_coupon_code = None
            cart.discount_amount = 0.0
            cart.discount_type = None
            
            # Commit all changes
            await db.commit()
            await db.refresh(new_order)
            
            # Schedule order confirmation email as a background task
            background_tasks.add_task(self.send_order_confirmation, new_order, db)
            
            return new_order
            
        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # TODO Remove debugging step
            print(f"Error creating order: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to create order: {str(e)}")

    async def get_order_by_id(self, order_id: int, user_id: Optional[int], db: AsyncSession) -> Order:
        """
        Get order by ID
        If user_id is provided, ensure the order belongs to that user
        """
        try:
            query = select(Order).where(Order.id == order_id)
            
            # If user_id is provided, check ownership
            if user_id is not None:
                query = query.where(Order.customer_id == user_id)
                
            result = await db.execute(query)
            order = result.scalars().first()
            
            if not order:
                raise NotFoundException(f"Order with ID {order_id} not found")
                
            return order
            
        except Exception as e:
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, NotFoundException):
                raise
                
            # Log the error
            print(f"Error retrieving order: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to retrieve order: {str(e)}")

    async def get_user_orders(
        self, 
        user_id: int,
        db: AsyncSession,
        skip: int = 0, 
        limit: int = 10
    ) -> List[Order]:
        """Get all orders for a specific user"""
        try:
            query = (
                select(Order)
                .where(Order.customer_id == user_id)
                .order_by(Order.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            result = await db.execute(query)
            orders = result.scalars().all()
            
            return orders
            
        except Exception as e:
            # Log the error
            print(f"Error retrieving user orders: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to retrieve orders: {str(e)}")

    async def get_order_detail(self, order_id: int, user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Get detailed order information including items and services"""
        try:
            order = await self.get_order_by_id(order_id, user_id, db)
            
            # Get order items with product details
            items_query = (
                select(OrderItem, Product)
                .join(Product)
                .where(OrderItem.order_id == order_id)
            )
            items_result = await db.execute(items_query)
            items_data = items_result.all()
            
            # Get order services with service details
            services_query = (
                select(OrderServiceModel, Service)
                .join(Service)
                .where(OrderServiceModel.order_id == order_id)
            )
            services_result = await db.execute(services_query)
            services_data = services_result.all()
            
            # Prepare response format
            items = []
            for item, product in items_data:
                items.append({
                    "id": item.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "quantity": item.quantity,
                    "price": item.price,
                    "discount": item.discount,
                    "total": item.price * item.quantity - item.discount
                })
            
            services = []
            for service_item, service in services_data:
                services.append({
                    "id": service_item.id,
                    "service_id": service.id,
                    "service_name": service.name,
                    "price": service_item.price,
                    "appointment_id": service_item.appointment_id
                })
            
            # Format order details
            order_detail = {
                "id": order.id,
                "order_number": order.order_number,
                "customer_id": order.customer_id,
                "status": order.status,
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "subtotal": order.subtotal,
                "tax": order.tax,
                "shipping_cost": order.shipping_cost,
                "discount": order.discount,
                "total": order.total,
                "items": items,
                "services": services,
                "notes": order.notes,
                "tracking_number": order.tracking_number,
                "estimated_delivery": order.estimated_delivery,
                "created_at": order.created_at,
                "updated_at": order.updated_at
            }
            
            return order_detail
            
        except Exception as e:
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error retrieving order details: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to retrieve order details: {str(e)}")

    # Admin-specific order management methods
    async def get_all_orders_admin(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        status_filter: Optional[str] = None,
        payment_method: Optional[str] = None,
        customer_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[Order]:
        """Get all orders in the system with filtering (Admin only)"""
        try:
            query = select(Order)
            
            # Apply filters
            if status_filter:
                query = query.where(Order.status == status_filter)
            
            if payment_method:
                query = query.where(Order.payment_method == payment_method)
            
            if customer_id:
                query = query.where(Order.customer_id == customer_id)
            
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, "%Y-%m-%d")
                    query = query.where(Order.created_at >= from_date)
                except ValueError:
                    pass  # Invalid date format, ignore filter
            
            if date_to:
                try:
                    to_date = datetime.strptime(date_to, "%Y-%m-%d")
                    # Add 1 day to include the entire end date
                    to_date = to_date + timedelta(days=1)
                    query = query.where(Order.created_at < to_date)
                except ValueError:
                    pass  # Invalid date format, ignore filter
            
            # Apply sorting
            if hasattr(Order, sort_by):
                order_field = getattr(Order, sort_by)
                if sort_order.lower() == "desc":
                    query = query.order_by(order_field.desc())
                else:
                    query = query.order_by(order_field.asc())
            else:
                # Default sorting
                query = query.order_by(Order.created_at.desc())
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            result = await db.execute(query)
            orders = result.scalars().all()
            
            return orders
            
        except Exception as e:
            print(f"Error retrieving all orders: {str(e)}")
            raise BadRequestException(f"Failed to retrieve orders: {str(e)}")

    async def get_order_by_id_admin(self, order_id: int, db: AsyncSession) -> Order:
        """Get order by ID with admin privileges (no user ownership check)"""
        try:
            query = select(Order).where(Order.id == order_id)
            result = await db.execute(query)
            order = result.scalars().first()
            
            if not order:
                raise NotFoundException(f"Order with ID {order_id} not found")
            
            return order
            
        except NotFoundException:
            raise
        except Exception as e:
            print(f"Error retrieving order by ID: {str(e)}")
            raise BadRequestException(f"Failed to retrieve order: {str(e)}")
            raise BadRequestException(f"Failed to retrieve order details: {str(e)}")

    async def update_order_status(
        self, 
        order_id: int, 
        status: OrderStatus, 
        admin_id: int,
        db: AsyncSession,
        notes: Optional[str] = None,
        location: Optional[str] = None,
        background_tasks: BackgroundTasks = None
    ) -> Order:
        """Update an order's status (admin function)"""
        try:
            order = await self.get_order_by_id(order_id, None, db)
            
            # Record previous status for history
            previous_status = order.status
            
            # Format timestamp in a cleaner way
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            # Check if status is actually changing
            if previous_status == status:
                # If status isn't changing but there are notes, add them
                if notes and notes.strip():
                    new_note = f"[{timestamp}] Note: {notes}"
                    
                    # If there are existing notes, append with separation
                    if order.notes and order.notes.strip() and not order.notes.startswith("string"):
                        order.notes = f"{order.notes}\n\n{new_note}"
                    else:
                        # If notes are empty or just "string", replace entirely
                        order.notes = new_note
            else:
                # Update order status
                order.status = status
                
                # Format previous and new status values (remove OrderStatus. prefix)
                prev_status_str = previous_status.value if hasattr(previous_status, 'value') else str(previous_status)
                new_status_str = status.value if hasattr(status, 'value') else str(status)
                
                if prev_status_str.startswith("OrderStatus."):
                    prev_status_str = prev_status_str.replace("OrderStatus.", "")
                    
                if new_status_str.startswith("OrderStatus."):
                    new_status_str = new_status_str.replace("OrderStatus.", "")
                
                # Create status change entry
                status_note = f"[{timestamp}] Status updated: {prev_status_str} → {new_status_str}"
                
                # Add notes if provided
                if notes and notes.strip():
                    # Don't add "string" as a note
                    if notes != "string":
                        admin_note = f"Note: {notes}"
                        new_entry = f"{status_note}\n{admin_note}"
                    else:
                        new_entry = status_note
                else:
                    new_entry = status_note
                
                # Update the notes field
                if order.notes and order.notes.strip() and not order.notes.startswith("string"):
                    order.notes = f"{order.notes}\n\n{new_entry}"
                else:
                    # If notes are empty or just "string", replace entirely
                    order.notes = new_entry
            
            # Create status history entry
            status_history = OrderStatusHistory(
                order_id=order_id,
                previous_status=previous_status,
                new_status=status,
                changed_by_id=admin_id,
                notes=notes if notes != "string" else None  # Don't store "string" as a note
            )
            db.add(status_history)
            
            # Initialize tracking_data to None
            tracking_data = None
            
            # Special handling for specific statuses
            if status == OrderStatus.SHIPPED:
                # Generate tracking number if not present
                if not order.tracking_number:
                    order.tracking_number = f"TRK-{uuid.uuid4().hex[:10].upper()}"
                    
                # Create tracking data dictionary
                tracking_data = {
                    "status": status,
                    "location": location or "Distribution center",
                    "checkpoint": {
                        "status": status,
                        "location": location or "Distribution center",
                        "description": notes or f"Order {status.value.lower()}"
                    }
                }
                
                # Update tracking info in the same transaction
                if tracking_data:
                    await self._update_tracking_info_same_transaction(
                        order_id=order_id,
                        admin_id=admin_id,
                        tracking_data=tracking_data,
                        db=db
                    )
                    
            elif status == OrderStatus.DELIVERED:
                tracking_data = {
                    "status": status,
                    "location": location or "Delivery address",
                    "checkpoint": {
                        "status": status,
                        "location": location or "Delivery address",
                        "description": notes or "Order delivered to customer"
                    }
                }
                
                # Update tracking info in the same transaction
                if tracking_data:
                    await self._update_tracking_info_same_transaction(
                        order_id=order_id,
                        admin_id=admin_id,
                        tracking_data=tracking_data,
                        db=db
                    )
                    
                if order.payment_method == PaymentMethod.CASH_ON_DELIVERY:
                    # When order is delivered with cash on delivery, update payment status to completed
                    order.payment_status = PaymentStatus.COMPLETED
                    
                    # Create a payment transaction
                    payment = PaymentTransaction(
                        order_id=order_id,
                        transaction_id=f"COD-{uuid.uuid4().hex[:10].upper()}",
                        amount=order.total,
                        currency=order.payment_currency,
                        method=order.payment_method,
                        status=PaymentStatus.COMPLETED,
                        details={"payment_method": "cash_on_delivery", "collected_by_id": admin_id}
                    )
                    db.add(payment)
                    
            elif status == OrderStatus.PROCESSING:
                # Create tracking data for processing
                tracking_data = {
                    "status": status,
                    "location": "Warehouse",
                    "checkpoint": {
                        "status": status,
                        "location": "Warehouse",
                        "description": "Order is being prepared for shipment"
                    }
                }
                
                # Update tracking info in the same transaction
                if tracking_data:
                    await self._update_tracking_info_same_transaction(
                        order_id=order_id,
                        admin_id=admin_id,
                        tracking_data=tracking_data,
                        db=db
                    )
            
            # Commit the order status change
            await db.commit()
            await db.refresh(order)
            
            # Send notification based on status change
            if background_tasks:
                # Add to background tasks for async processing
                background_tasks.add_task(self._send_order_status_notification_background, order.id)
            
            return order

        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error updating order status: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to update order status: {str(e)}")

    async def _update_tracking_info_same_transaction(
        self,
        order_id: int,
        admin_id: int,
        tracking_data: Dict[str, Any],
        db: AsyncSession
    ) -> None:
        """Update shipment tracking information within the same transaction"""
        # Get or create shipment tracking
        query = select(ShipmentTracking).where(ShipmentTracking.order_id == order_id)
        result = await db.execute(query)
        tracking = result.scalars().first()
        
        if not tracking:
            # Create new tracking record
            estimated_delivery = tracking_data.get("estimated_delivery")
            if estimated_delivery:
                estimated_delivery = self._convert_to_naive_datetime(estimated_delivery)
                
            tracking = ShipmentTracking(
                order_id=order_id,
                status=tracking_data.get("status"),
                location=tracking_data.get("location"),
                carrier=tracking_data.get("carrier"),
                estimated_delivery=estimated_delivery,
                tracking_number=tracking_data.get("tracking_number"),
                details=tracking_data.get("details", {})
            )
            db.add(tracking)
            
            # Get the order to update tracking information
            order = await self.get_order_by_id(order_id, None, db)
            
            # Update order tracking number if provided
            if tracking_data.get("tracking_number"):
                order.tracking_number = tracking_data["tracking_number"]
                
            # Update estimated delivery if provided
            if estimated_delivery:
                order.estimated_delivery = estimated_delivery
        else:
            # Update tracking information
            if tracking_data.get("status"):
                tracking.status = tracking_data["status"]
                
            if tracking_data.get("location"):
                tracking.location = tracking_data["location"]
                
            if tracking_data.get("carrier"):
                tracking.carrier = tracking_data["carrier"]
                
            if tracking_data.get("estimated_delivery"):
                estimated_delivery = self._convert_to_naive_datetime(tracking_data["estimated_delivery"])
                tracking.estimated_delivery = estimated_delivery
                
                # Update order estimated delivery
                order = await self.get_order_by_id(order_id, None, db)
                order.estimated_delivery = estimated_delivery
                
            if tracking_data.get("tracking_number"):
                tracking.tracking_number = tracking_data["tracking_number"]
                
                # Update order tracking number
                order = await self.get_order_by_id(order_id, None, db)
                order.tracking_number = tracking_data["tracking_number"]
                
            if tracking_data.get("details"):
                # Merge details instead of replacing
                if isinstance(tracking.details, dict) and isinstance(tracking_data.get("details"), dict):
                    tracking.details = {
                        **(tracking.details or {}),
                        **tracking_data["details"]
                    }
                else:
                    tracking.details = tracking_data.get("details", {})
                    
        # Add checkpoint if provided
        if tracking_data.get("checkpoint"):
            # Need to flush tracking first if it's new
            if tracking.id is None:
                await db.flush()
                
            # Get checkpoint timestamp and convert if timezone-aware
            checkpoint_timestamp = tracking_data["checkpoint"].get("timestamp", datetime.now())
            if checkpoint_timestamp:
                checkpoint_timestamp = self._convert_to_naive_datetime(checkpoint_timestamp)
                
            checkpoint = ShipmentCheckpoint(
                shipment_id=tracking.id,
                status=tracking_data["checkpoint"].get("status", tracking.status),
                location=tracking_data["checkpoint"].get("location", tracking.location),
                description=tracking_data["checkpoint"].get("description"),
                timestamp=checkpoint_timestamp
            )
            db.add(checkpoint)

    async def _send_order_status_notification_background(self, order_id: int) -> None:
        """Background task to send order status notification"""
        # Create a new session for the background task
        db_generator = get_db()
        db = await anext(db_generator)
        try:
            order = await self.get_order_by_id(order_id, None, db)
            customer = await self._get_user_by_id(order.customer_id, db)
            
            # Get tracking info if available
            tracking_info = await self.get_tracking_info(order.id, order.customer_id, db)
            
            order_data = {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status.value if hasattr(order.status, 'value') else str(order.status),
                "customer_name": getattr(customer, 'full_name', customer.email),
                "frontend_url": Config.DOMAIN,
                "current_year": datetime.now().year
            }
            
            # Send email
            email_service = EmailService()
            await email_service.send_order_tracking_update(
                to_email=customer.email,
                order_data=order_data,
                tracking_data=tracking_info
            )
        except Exception as e:
            print(f"Background notification error: {str(e)}")
        finally:
            await db.close()

    async def get_tracking_info(self, order_id: int, user_id: Optional[int], db: AsyncSession) -> Dict[str, Any]:
        """Get tracking information for an order"""
        try:
            # Check if user can access this order
            order = await self.get_order_by_id(order_id, user_id, db)
            
            # Get shipment tracking
            query = select(ShipmentTracking).where(ShipmentTracking.order_id == order_id)
            result = await db.execute(query)
            tracking = result.scalars().first()
            
            if not tracking:
                # Return basic info if no detailed tracking exists
                return {
                    "order_id": order.id,
                    "order_number": order.order_number,
                    "status": order.status.value,
                    "tracking_number": order.tracking_number,
                    "estimated_delivery": order.estimated_delivery,
                    "checkpoints": []
                }
                
            # Get checkpoints
            checkpoints_query = select(ShipmentCheckpoint).where(
                ShipmentCheckpoint.shipment_id == tracking.id
            ).order_by(ShipmentCheckpoint.timestamp.desc())
            checkpoints_result = await db.execute(checkpoints_query)
            checkpoints_data = checkpoints_result.scalars().all()
            
            # Format response with checkpoints
            checkpoints = [
                {
                    "id": cp.id,
                    "status": cp.status.value if hasattr(cp.status, 'value') else cp.status,
                    "location": cp.location,
                    "timestamp": cp.timestamp,
                    "description": cp.description
                } 
                for cp in checkpoints_data
            ]
            
            return {
                "id": tracking.id,
                "order_id": tracking.order_id,
                "order_number": order.order_number,
                "status": tracking.status.value if hasattr(tracking.status, 'value') else tracking.status,
                "location": tracking.location,
                "carrier": tracking.carrier,
                "tracking_number": tracking.tracking_number or order.tracking_number,
                "estimated_delivery": tracking.estimated_delivery or order.estimated_delivery,
                "details": tracking.details or {},
                "checkpoints": checkpoints
            }
        
        except Exception as e:
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error retrieving tracking info: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to retrieve tracking information: {str(e)}")

    async def update_tracking_info(
        self,
        order_id: int,
        admin_id: int,
        tracking_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Update shipment tracking information"""
        try:
            order = await self.get_order_by_id(order_id, None, db)
            
            # Use the existing method to update tracking in the database
            await self._update_tracking_info_same_transaction(
                order_id=order_id,
                admin_id=admin_id,
                tracking_data=tracking_data,
                db=db
            )
            
            # Commit the changes
            await db.commit()
            
            # Return updated tracking info
            return await self.get_tracking_info(order_id, None, db)
            
        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error updating tracking info: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to update tracking information: {str(e)}")