import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_, func, delete

from ..models import Cart, CartItem, CartServiceItem, Order, OrderItem, OrderService
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
                order_service = OrderService(
                    order_id=new_order.id,
                    service_id=service_item.service_id,
                    price=service.price,
                    appointment_id=appointment_id
                )
                db.add(order_service)
                
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
                select(OrderService, Service)
                .join(Service)
                .where(OrderService.order_id == order_id)
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
            
            # Update order status
            order.status = status
            
            # Add notes if provided
            if notes:
                if order.notes:
                    order.notes = f"{order.notes}\n[{datetime.now()}] Status changed from {previous_status} to {status}: {notes}"
                else:
                    order.notes = f"[{datetime.now()}] Status changed from {previous_status} to {status}: {notes}"
            
            # Create status history entry
            status_history = OrderStatusHistory(
                order_id=order_id,
                previous_status=previous_status,
                new_status=status,
                changed_by_id=admin_id,
                notes=notes
            )
            db.add(status_history)
            
            # Special handling for specific statuses
            if status == OrderStatus.SHIPPED:
                # Generate tracking number if not present
                if not order.tracking_number:
                    order.tracking_number = f"TRK-{uuid.uuid4().hex[:10].upper()}"
                    
                # Create tracking checkpoint for shipping
                await self.update_tracking_info(
                    order_id=order_id,
                    admin_id=admin_id,
                    tracking_data={
                        "status": status,
                        "location": location or "Distribution center",
                        "checkpoint": {
                            "status": status,
                            "location": location or "Distribution center",
                            "description": notes or f"Order {status.value.lower()}"
                        }
                    },
                    db=db
                )
            elif status == OrderStatus.DELIVERED:
                # Create tracking checkpoint for delivery
                await self.update_tracking_info(
                    order_id=order_id,
                    admin_id=admin_id,
                    tracking_data={
                        "status": status,
                        "location": location or "Delivery address",
                        "checkpoint": {
                            "status": status,
                            "location": location or "Delivery address",
                            "description": notes or "Order delivered to customer"
                        }
                    },
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
                    
            # For other status changes that warrant tracking updates
            elif status == OrderStatus.PROCESSING:
                # Create tracking checkpoint for processing
                await self.update_tracking_info(
                    order_id=order_id,
                    admin_id=admin_id,
                    tracking_data={
                        "status": status,
                        "location": "Warehouse",
                        "checkpoint": {
                            "status": status,
                            "location": "Warehouse",
                            "description": "Order is being prepared for shipment"
                        }
                    },
                    db=db
                )
            
            await db.commit()
            await db.refresh(order)
            
            # Send notification based on status change
            if background_tasks:
                background_tasks.add_task(self.send_order_status_notification, order)
            else:
                # Fallback if no background_tasks is provided
                await self.send_order_status_notification(order)
            
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

    async def update_payment_status(
        self, 
        order_id: int, 
        payment_status: PaymentStatus,
        db: AsyncSession,
        transaction_details: Optional[Dict[str, Any]] = None
    ) -> Order:
        """Update an order's payment status"""
        try:
            order = await self.get_order_by_id(order_id, None, db)
            
            # Record previous status
            previous_status = order.payment_status
            
            # Update payment status
            order.payment_status = payment_status
            
            # If payment is complete, record transaction details
            if payment_status == PaymentStatus.COMPLETED and transaction_details:                
                # Create payment transaction record
                payment = PaymentTransaction(
                    order_id=order_id,
                    transaction_id=transaction_details.get("transaction_id"),
                    amount=transaction_details.get("amount", order.total),
                    currency=transaction_details.get("currency", order.payment_currency),
                    method=order.payment_method,
                    status=payment_status,
                    details=transaction_details
                )
                db.add(payment)
                
                # If order was pending payment and now paid, update order status too
                if order.status == OrderStatus.PENDING:
                    order.status = OrderStatus.PROCESSING
            
            await db.commit()
            await db.refresh(order)
            
            # Notify user of payment status change
            if previous_status != payment_status:
                await self.send_payment_status_notification(order)
            
            return order
            
        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error updating payment status: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to update payment status: {str(e)}")

    async def cancel_order(
        self, 
        order_id: int, 
        user_id: int, 
        reason: str,
        db: AsyncSession
    ) -> Order:
        """Cancel an order (customer function)"""
        try:
            order = await self.get_order_by_id(order_id, user_id, db)
            
            # Check if the order can be canceled
            if order.status in [OrderStatus.DELIVERED, OrderStatus.COMPLETED, OrderStatus.CANCELLED]:
                raise BadRequestException(f"Cannot cancel order in status {order.status}")
            
            # Get all order items
            items_query = select(OrderItem).where(OrderItem.order_id == order_id)
            result = await db.execute(items_query)
            items = result.scalars().all()
            
            # Return items to inventory
            for item in items:
                product = await db.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity
            
            # Cancel any appointments
            services_query = select(OrderService).where(OrderService.order_id == order_id)
            services_result = await db.execute(services_query)
            service_items = services_result.scalars().all()
            
            for service_item in service_items:
                if service_item.appointment_id:
                    appointment = await db.get(Appointment, service_item.appointment_id)
                    if appointment and appointment.status != "completed":
                        appointment.status = "cancelled"
                        appointment.notes = f"{appointment.notes or ''}\nCancelled due to order cancellation: {reason}"
            
            # Create cancellation record            
            cancellation = OrderCancellation(
                order_id=order_id,
                cancelled_by_id=user_id,
                reason=reason,
                cancelled_at=datetime.now()
            )
            db.add(cancellation)
            
            # Update order status
            order.status = OrderStatus.CANCELLED
            
            # Add cancellation reason to notes
            if order.notes:
                order.notes = f"{order.notes}\n[{datetime.now()}] Cancelled by customer: {reason}"
            else:
                order.notes = f"[{datetime.now()}] Cancelled by customer: {reason}"
            
            await db.commit()
            await db.refresh(order)
            
            # Send cancellation notification
            await self.send_order_cancellation_notification(order, reason)
            
            return order
            
        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error cancelling order: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to cancel order: {str(e)}")

    async def process_refund(
        self, 
        order_id: int, 
        admin_id: int, 
        amount: float, 
        reason: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Process a refund for an order (admin function)"""
        try:
            order = await self.get_order_by_id(order_id, None, db)
            
            # Check if order is eligible for refund
            if order.status not in [OrderStatus.CANCELLED, OrderStatus.RETURNED, OrderStatus.COMPLETED, OrderStatus.DELIVERED]:
                raise BadRequestException(f"Cannot process refund for order in status {order.status}")
            
            # Validate refund amount
            if amount <= 0 or amount > order.total:
                raise BadRequestException(f"Invalid refund amount. Must be between 0 and {order.total}")
            
            # Create refund record
            refund = Refund(
                order_id=order_id,
                amount=amount,
                reason=reason,
                processed_by_id=admin_id,
                status="pending",  # Assume refunds need approval/processing
                processed_at=datetime.now()
            )
            db.add(refund)
            
            # Update order notes
            if order.notes:
                order.notes = f"{order.notes}\n[{datetime.now()}] Refund of {amount} initiated: {reason}"
            else:
                order.notes = f"[{datetime.now()}] Refund of {amount} initiated: {reason}"
                
                await db.commit()
                await db.refresh(refund)
                
                # Process the refund (in real implementation, connect to payment gateway)
                # This is a placeholder for the actual payment processing logic
                refund_result = {
                    "refund_id": refund.id,
                    "amount": amount,
                    "status": "pending",
                    "transaction_id": f"REF-{uuid.uuid4().hex[:10].upper()}"
                }
                
                # Send refund notification
                await self.send_refund_notification(order, refund)
                
                return refund_result
            
        except Exception as e:
            # Rollback transaction in case of any error
            await db.rollback()
            
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error processing refund: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to process refund: {str(e)}")

    async def admin_search_orders(
        self,
        db: AsyncSession,
        search_term: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        customer_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Order], int]:
        """Search orders with various filters (admin function)"""
        try:
            # Base query
            query = select(Order)
            count_query = select(func.count(Order.id))
            
            # Apply filters
            if search_term:
                query = query.where(
                    or_(
                        Order.order_number.ilike(f"%{search_term}%"),
                        Order.notes.ilike(f"%{search_term}%"),
                        Order.tracking_number.ilike(f"%{search_term}%")
                    )
                )
                count_query = count_query.where(
                    or_(
                        Order.order_number.ilike(f"%{search_term}%"),
                        Order.notes.ilike(f"%{search_term}%"),
                        Order.tracking_number.ilike(f"%{search_term}%")
                    )
                )
            
            if status:
                query = query.where(Order.status == status)
                count_query = count_query.where(Order.status == status)
            
            if payment_status:
                query = query.where(Order.payment_status == payment_status)
                count_query = count_query.where(Order.payment_status == payment_status)
            
            if start_date:
                query = query.where(Order.created_at >= start_date)
                count_query = count_query.where(Order.created_at >= start_date)
            
            if end_date:
                query = query.where(Order.created_at <= end_date)
                count_query = count_query.where(Order.created_at <= end_date)
            
            if customer_id:
                query = query.where(Order.customer_id == customer_id)
                count_query = count_query.where(Order.customer_id == customer_id)
            
            # Get total count
            count_result = await db.execute(count_query)
            total_count = count_result.scalar() or 0
            
            # Apply pagination and ordering
            query = (
                query
                .order_by(Order.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            # Execute query
            result = await db.execute(query)
            orders = result.scalars().all()
            
            return orders, total_count
            
        except Exception as e:
            # Log the error
            print(f"Error searching orders: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to search orders: {str(e)}")

    async def get_order_statistics(
        self,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get order statistics for dashboard (admin function)"""
        try:
            # Set default date range to current month if not specified
            if not start_date:
                start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if not end_date:
                end_date = datetime.now()
            
            # Base queries
            orders_query = select(Order).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            
            # Get total orders
            total_count_query = select(func.count(Order.id)).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            total_count_result = await db.execute(total_count_query)
            total_orders = total_count_result.scalar() or 0
            
            # Get total revenue
            revenue_query = select(func.sum(Order.total)).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.payment_status == PaymentStatus.COMPLETED
                )
            )
            revenue_result = await db.execute(revenue_query)
            total_revenue = revenue_result.scalar() or 0.0
            
            # Get orders by status
            status_counts = {}
            for status in OrderStatus:
                status_query = select(func.count(Order.id)).where(
                    and_(
                        Order.created_at >= start_date,
                        Order.created_at <= end_date,
                        Order.status == status
                    )
                )
                status_result = await db.execute(status_query)
                status_counts[status] = status_result.scalar() or 0
            
            # Get products sold
            products_sold_query = select(func.sum(OrderItem.quantity)).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status != OrderStatus.CANCELLED
                )
            )
            products_sold_result = await db.execute(products_sold_query)
            products_sold = products_sold_result.scalar() or 0
            
            # Build statistics response
            stats = {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "status_breakdown": status_counts,
                "products_sold": products_sold,
                "start_date": start_date,
                "end_date": end_date
            }
            
            return stats
            
        except Exception as e:
            # Log the error
            print(f"Error generating order statistics: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to generate order statistics: {str(e)}")

    async def update_tracking_info(
        self,
        order_id: int,
        admin_id: int,
        tracking_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        try:
            """Update shipment tracking information"""
            order = await self.get_order_by_id(order_id, None, db)
            
            # Get or create shipment tracking
            # Check if tracking exists
            query = select(ShipmentTracking).where(ShipmentTracking.order_id == order_id)
            result = await db.execute(query)
            tracking = result.scalars().first()
            
            if not tracking:
                # Create new tracking record
                tracking = ShipmentTracking(
                    order_id=order_id,
                    status=tracking_data.get("status", order.status),
                    location=tracking_data.get("location"),
                    carrier=tracking_data.get("carrier"),
                    estimated_delivery=tracking_data.get("estimated_delivery"),
                    tracking_number=tracking_data.get("tracking_number") or order.tracking_number,
                    details=tracking_data.get("details", {})
                )
                db.add(tracking)
                
                # Update order tracking number if provided
                if tracking_data.get("tracking_number"):
                    order.tracking_number = tracking_data["tracking_number"]
                    
                # Update estimated delivery if provided
                if tracking_data.get("estimated_delivery"):
                    order.estimated_delivery = tracking_data["estimated_delivery"]
            else:
                # Update tracking information
                if tracking_data.get("status"):
                    tracking.status = tracking_data["status"]
                    
                if tracking_data.get("location"):
                    tracking.location = tracking_data["location"]
                    
                if tracking_data.get("carrier"):
                    tracking.carrier = tracking_data["carrier"]
                    
                if tracking_data.get("estimated_delivery"):
                    tracking.estimated_delivery = tracking_data["estimated_delivery"]
                    order.estimated_delivery = tracking_data["estimated_delivery"]
                    
                if tracking_data.get("tracking_number"):
                    tracking.tracking_number = tracking_data["tracking_number"]
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
                # Need to commit tracking first if it's new
                if tracking.id is None:
                    await db.flush()
                    
                checkpoint = ShipmentCheckpoint(
                    shipment_id=tracking.id,
                    status=tracking_data["checkpoint"].get("status", tracking.status),
                    location=tracking_data["checkpoint"].get("location", tracking.location),
                    description=tracking_data["checkpoint"].get("description"),
                    timestamp=tracking_data["checkpoint"].get("timestamp", datetime.now())
                )
                db.add(checkpoint)
                
            await db.commit()
            
            # Refresh tracking to get related checkpoints
            await db.refresh(tracking)
            
            # Format response
            checkpoints = [
                {
                    "id": cp.id,
                    "status": cp.status,
                    "location": cp.location,
                    "timestamp": cp.timestamp,
                    "description": cp.description
                } 
                for cp in tracking.checkpoints
            ]
            
            tracking_info = {
                "id": tracking.id,
                "order_id": tracking.order_id,
                "order_number": order.order_number,
                "status": tracking.status,
                "location": tracking.location,
                "carrier": tracking.carrier,
                "tracking_number": tracking.tracking_number,
                "estimated_delivery": tracking.estimated_delivery,
                "details": tracking.details,
                "checkpoints": checkpoints
            }
            
            return tracking_info
        except Exception as e:
            await db.rollback()
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
            # TODO: REMOVE DEBUGGING STEP
            print(f"Error updating tracking info: {str(e)}")
            raise BadRequestException(f"Failed to update tracking information: {str(e)}")

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
                    "status": order.status,
                    "tracking_number": order.tracking_number,
                    "estimated_delivery": order.estimated_delivery,
                    "checkpoints": []
                }
                    
            # Format response with checkpoints
            checkpoints = [
                {
                    "id": cp.id,
                    "status": cp.status,
                    "location": cp.location,
                    "timestamp": cp.timestamp,
                    "description": cp.description
                } 
                for cp in tracking.checkpoints
            ]
            
            return {
                "id": tracking.id,
                "order_id": tracking.order_id,
                "order_number": order.order_number,
                "status": tracking.status,
                "location": tracking.location,
                "carrier": tracking.carrier,
                "tracking_number": tracking.tracking_number,
                "estimated_delivery": tracking.estimated_delivery,
                "details": tracking.details,
                "checkpoints": checkpoints
            }
            
        except Exception as e:
            # Re-raise HTTP exceptions as they are intentional
            if isinstance(e, (NotFoundException, BadRequestException)):
                raise
                
            # Log the error
            print(f"Error retrieving tracking information: {str(e)}")
            
            # Raise a generic exception with a user-friendly message
            raise BadRequestException(f"Failed to retrieve tracking information: {str(e)}")

    async def send_order_confirmation(self, order: Order, db: AsyncSession) -> None:
        """Send order confirmation email"""
        try:            
            # Get user details
            customer = await self._get_user_by_id(order.customer_id, db)
            
            # Get order details including items and services
            order_details = await self.get_order_detail(order.id, order.customer_id, db)
            
            # Convert SQLAlchemy objects to dictionaries
            order_data = {
                "id": order.id,
                "order_number": order.order_number,
                "created_at": order.created_at,
                "payment_method": order.payment_method,
                "subtotal": order.subtotal,
                "discount": order.discount,
                "shipping_cost": order.shipping_cost,
                "tax": order.tax,
                "total": order.total,
                "items": order_details.get("items", []),
                "services": order_details.get("services", []),
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "frontend_url": Config.FRONTEND_URL,
                "customer_name": customer.full_name if hasattr(customer, 'full_name') else customer.email,
                "current_year": datetime.now().year
            }
            
            # Send email
            email_service = EmailService()
            await email_service.send_order_confirmation(customer.email, order_data)
            
        except Exception as e:
            print(f"Error sending order confirmation email: {str(e)}")

    async def send_order_status_notification(self, order: Order) -> None:
        """Send notification when order status changes"""
        try:
            # Get user details
            db_session = get_db()
            async with db_session() as db:
                customer = await self.get_user_by_id(order.customer_id, db)
                
                # Get tracking info if available
                tracking_info = await self.get_tracking_info(order.id, order.customer_id, db)
                
                # Get basic order data
                order_data = {
                    "id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "customer_name": customer.full_name if hasattr(customer, 'full_name') else customer.email,
                    "frontend_url": Config.FRONTEND_URL,
                    "current_year": datetime.datetime.now().year
                }
                
                # Send email
                email_service = EmailService()
                await email_service.send_order_tracking_update(
                    to_email=customer.email,
                    order_data=order_data,
                    tracking_data=tracking_info
                )
                
        except Exception as e:
            # For notification methods, we don't want to break the main flow if they fail
            # Just log the error
            print(f"Error sending order status notification: {str(e)}")

    async def send_payment_status_notification(self, order: Order) -> None:
        """Send notification when payment status changes"""
        try:
            # Get user details
            db_session = get_db()
            async with db_session() as db:
                customer = await self._get_user_by_id(order.customer_id, db)
                
                # Get order details
                order_details = await self.get_order_detail(order.id, order.customer_id, db)
                
                # Prepare email data
                customer_name = getattr(customer, 'full_name', None) or getattr(customer, 'name', None) or customer.email
                
                # Different subject lines based on payment status
                if order.payment_status == PaymentStatus.COMPLETED:
                    subject = f"Payment Received for Order #{order.order_number}"
                    template = "payment-confirmed.html"
                elif order.payment_status == PaymentStatus.FAILED:
                    subject = f"Payment Failed for Order #{order.order_number}"
                    template = "payment-failed.html"
                elif order.payment_status == PaymentStatus.REFUNDED:
                    subject = f"Refund Processed for Order #{order.order_number}"
                    template = "payment-refunded.html"
                else:
                    subject = f"Payment Update for Order #{order.order_number}"
                    template = "payment-status.html"
                
                # Prepare template data
                template_data = {
                    "customer_name": customer_name,
                    "customer_email": customer.email,
                    "order_number": order.order_number,
                    "payment_status": order.payment_status.value,
                    "order_total": order.total,
                    "currency": order.payment_currency or "KES",
                    "payment_method": order.payment_method.value,
                    "order_url": f"{Config.FRONTEND_URL}/orders/{order.id}",
                    "payment_url": f"{Config.FRONTEND_URL}/orders/{order.id}/payment",
                    "current_year": datetime.datetime.now().year,
                    "order": order_details
                }
                
                # Send email
                email_service = EmailService()
                await email_service.send_template_email(
                    to_email=customer.email,
                    subject=subject,
                    template_name=template,
                    context=template_data
                )
                
                # Consider sending an SMS notification for payment status
                if hasattr(customer, 'phone') and customer.phone:
                    await self._send_payment_status_sms(customer.phone, order)
                    
        except Exception as e:
            # For notification methods, we don't want to break the main flow if they fail
            # Just log the error
            print(f"Error sending payment status notification: {str(e)}")

    async def send_order_cancellation_notification(self, order: Order, reason: str) -> None:
        """Send notification when an order is cancelled"""
        try:
            # Get user details
            db_session = get_db()
            async with db_session() as db:
                customer = await self._get_user_by_id(order.customer_id, db)
                
                # Get order details
                order_details = await self.get_order_detail(order.id, order.customer_id, db)
                
                # Prepare email data
                customer_name = getattr(customer, 'full_name', None) or getattr(customer, 'name', None) or customer.email
                subject = f"Order #{order.order_number} Has Been Cancelled"
                
                # Prepare template data
                template_data = {
                    "customer_name": customer_name,
                    "customer_email": customer.email,
                    "order_number": order.order_number,
                    "cancel_reason": reason,
                    "cancelled_date": datetime.datetime.now(),
                    "order_date": order.created_at,
                    "order_total": order.total,
                    "payment_status": order.payment_status.value,
                    "payment_method": order.payment_method.value,
                    "refund_eligible": order.payment_status == PaymentStatus.COMPLETED,
                    "currency": order.payment_currency or "KES",
                    "support_email": Config.SUPPORT_EMAIL or "support@dira.health",
                    "support_phone": Config.SUPPORT_PHONE or "+123456789",
                    "order_url": f"{Config.FRONTEND_URL}/orders/{order.id}",
                    "shop_url": f"{Config.FRONTEND_URL}/shop",
                    "current_year": datetime.datetime.now().year,
                    "order": order_details
                }
                
                # Send email
                email_service = EmailService()
                await email_service.send_template_email(
                    to_email=customer.email,
                    subject=subject,
                    template_name="order-cancelled.html",
                    context=template_data
                )
                
        except Exception as e:
            # For notification methods, we don't want to break the main flow if they fail
            # Just log the error
            print(f"Error sending order cancellation notification: {str(e)}")

    async def send_refund_notification(self, order: Order, refund: Any) -> None:
        """Send notification when a refund is processed"""
        try:
            # Get user details
            db_session = get_db()
            async with db_session() as db:
                customer = await self._get_user_by_id(order.customer_id, db)
                
                # Get order details
                order_details = await self.get_order_detail(order.id, order.customer_id, db)
                
                # Prepare email data
                customer_name = getattr(customer, 'full_name', None) or getattr(customer, 'name', None) or customer.email
                subject = f"Refund Processed for Order #{order.order_number}"
                
                # Prepare template data
                template_data = {
                    "customer_name": customer_name,
                    "customer_email": customer.email,
                    "order_number": order.order_number,
                    "refund_amount": refund.amount,
                    "refund_date": refund.processed_at,
                    "refund_reason": refund.reason,
                    "refund_status": refund.status,
                    "refund_id": str(refund.id),
                    "order_total": order.total,
                    "currency": order.payment_currency or "KES",
                    "payment_method": order.payment_method.value,
                    "payment_account": "Original payment method",
                    "estimated_arrival": (datetime.datetime.now() + datetime.timedelta(days=5)).date(),
                    "support_email": Config.SUPPORT_EMAIL or "support@dira.health",
                    "order_url": f"{Config.FRONTEND_URL}/orders/{order.id}",
                    "current_year": datetime.datetime.now().year,
                    "order": order_details
                }
                
                # Send email
                email_service = EmailService()
                await email_service.send_template_email(
                    to_email=customer.email,
                    subject=subject,
                    template_name="order-refund.html",
                    context=template_data
                )
                
                # Consider sending an SMS notification for the refund
                if hasattr(customer, 'phone') and customer.phone:
                    await self._send_refund_sms(customer.phone, order, refund)
                    
        except Exception as e:
            # For notification methods, we don't want to break the main flow if they fail
            # Just log the error
            print(f"Error sending refund notification: {str(e)}")

    async def _send_payment_status_sms(self, phone_number: str, order: Order) -> None:
        """Send SMS notification for payment status"""
        # TODO SMS IMPLEMENTATION FOR SENDING PAYMENT STATUS
        print("Success:")

    async def _send_refund_sms(self, phone_number: str, order: Order, refund: Any) -> None:
        """Send SMS notification for refund"""
        # TODO SMS IMPLEMENTATION FOR SENDING REFUND SMS