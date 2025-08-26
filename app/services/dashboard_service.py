from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text, or_, case
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import List

from ..models.user import User
from ..models.product import Product
from ..models.category import Category
from ..models.order import Order
from ..models.order_item import OrderItem
from ..models.review import Review
from ..models.payment_transaction import PaymentTransaction
from ..enums import OrderStatus, PaymentStatus, UserRole
from ..schemas.dashboard import (
    DashboardResponse,
    SummaryStats,
    SalesStats,
    ProductStats,
    UserStats,
    OrderStats,
    ReviewStats,
    SystemAlerts,
    TopSellingProduct,
    LowStockProduct,
    CategorySummary,
    TopBuyer,
    LatestOrder,
    RecentReview,
    RevenueByCategoryItem
)


class DashboardService:
    
    async def get_dashboard_data(self, db: AsyncSession) -> DashboardResponse:
        """Get comprehensive dashboard data for admin"""
        
        # Get all data concurrently
        summary_data = await self._get_summary_stats(db)
        sales_data = await self._get_sales_stats(db)
        products_data = await self._get_product_stats(db)
        users_data = await self._get_user_stats(db)
        orders_data = await self._get_order_stats(db)
        reviews_data = await self._get_review_stats(db)
        revenue_by_category = await self._get_revenue_by_category(db)
        alerts_data = await self._get_system_alerts(db)
        
        return DashboardResponse(
            summary=summary_data,
            sales=sales_data,
            products=products_data,
            users=users_data,
            orders=orders_data,
            reviews=reviews_data,
            revenue_by_category=revenue_by_category,
            alerts=alerts_data,
            last_updated=datetime.utcnow()
        )
    
    async def _get_summary_stats(self, db: AsyncSession) -> SummaryStats:
        """Get high-level summary statistics"""
        
        # Get basic counts
        total_users = await db.scalar(select(func.count(User.id)))
        total_products = await db.scalar(select(func.count(Product.id)))
        total_categories = await db.scalar(select(func.count(Category.id)))
        total_orders = await db.scalar(select(func.count(Order.id)))
        
        # Get total sales
        total_sales = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(Order.status == OrderStatus.DELIVERED)
        ) or 0.0
        
        # Active users this month
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users_this_month = await db.scalar(
            select(func.count(func.distinct(Order.customer_id)))
            .where(Order.created_at >= thirty_days_ago)
        ) or 0
        
        # Conversion rate (users with orders / total users)
        users_with_orders = await db.scalar(
            select(func.count(func.distinct(Order.customer_id)))
        ) or 0
        conversion_rate = (users_with_orders / total_users * 100) if total_users > 0 else 0.0
        
        return SummaryStats(
            total_users=total_users or 0,
            total_products=total_products or 0,
            total_categories=total_categories or 0,
            total_orders=total_orders or 0,
            total_sales=total_sales,
            active_users_this_month=active_users_this_month,
            conversion_rate=round(conversion_rate, 2)
        )
    
    async def _get_sales_stats(self, db: AsyncSession) -> SalesStats:
        """Get sales statistics and trends"""
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        year_start = today_start.replace(month=1, day=1)
        
        # Sales amounts
        sales_today = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(and_(
                Order.status == OrderStatus.DELIVERED,
                Order.created_at >= today_start
            ))
        ) or 0.0
        
        sales_this_week = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(and_(
                Order.status == OrderStatus.DELIVERED,
                Order.created_at >= week_start
            ))
        ) or 0.0
        
        sales_this_month = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(and_(
                Order.status == OrderStatus.DELIVERED,
                Order.created_at >= month_start
            ))
        ) or 0.0
        
        sales_last_month = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(and_(
                Order.status == OrderStatus.DELIVERED,
                Order.created_at >= last_month_start,
                Order.created_at < month_start
            ))
        ) or 0.0
        
        sales_year_to_date = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
            .where(and_(
                Order.status == OrderStatus.DELIVERED,
                Order.created_at >= year_start
            ))
        ) or 0.0
        
        # Order counts
        orders_today = await db.scalar(
            select(func.count(Order.id))
            .where(Order.created_at >= today_start)
        ) or 0
        
        orders_this_week = await db.scalar(
            select(func.count(Order.id))
            .where(Order.created_at >= week_start)
        ) or 0
        
        orders_this_month = await db.scalar(
            select(func.count(Order.id))
            .where(Order.created_at >= month_start)
        ) or 0
        
        # Average order value
        avg_order_value = await db.scalar(
            select(func.coalesce(func.avg(Order.total), 0))
            .where(Order.status == OrderStatus.DELIVERED)
        ) or 0.0
        
        # Top selling products
        top_products = await self._get_top_selling_products(db)
        
        return SalesStats(
            today=sales_today,
            this_week=sales_this_week,
            this_month=sales_this_month,
            last_month=sales_last_month,
            year_to_date=sales_year_to_date,
            order_count_today=orders_today,
            order_count_this_week=orders_this_week,
            order_count_this_month=orders_this_month,
            average_order_value=round(avg_order_value, 2),
            top_selling_products=top_products
        )
    
    async def _get_top_selling_products(self, db: AsyncSession, limit: int = 5) -> List[TopSellingProduct]:
        """Get top selling products by units sold"""
        
        query = (
            select(
                Product.id,
                Product.name,
                Product.slug,
                func.coalesce(func.sum(OrderItem.quantity), 0).label('units_sold'),
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label('revenue')
            )
            .select_from(Product)
            .outerjoin(OrderItem)
            .outerjoin(Order)
            .where(Order.status == OrderStatus.DELIVERED)
            .group_by(Product.id, Product.name, Product.slug)
            .order_by(desc('units_sold'))
            .limit(limit)
        )
        
        result = await db.execute(query)
        products = result.fetchall()
        
        return [
            TopSellingProduct(
                product_id=p.id,
                name=p.name,
                slug=p.slug,
                units_sold=p.units_sold or 0,
                revenue=p.revenue or 0.0
            )
            for p in products
        ]
    
    async def _get_product_stats(self, db: AsyncSession) -> ProductStats:
        """Get product statistics"""
        
        total_products = await db.scalar(select(func.count(Product.id))) or 0
        active_products = await db.scalar(
            select(func.count(Product.id)).where(Product.is_active == True)
        ) or 0
        inactive_products = total_products - active_products
        
        out_of_stock = await db.scalar(
            select(func.count(Product.id)).where(Product.stock == 0)
        ) or 0
        
        # Low stock products (stock <= reorder_level or stock <= 10 if no reorder_level)
        low_stock_query = (
            select(Product)
            .where(and_(
                Product.stock > 0,
                or_(
                    and_(Product.reorder_level.is_not(None), Product.stock <= Product.reorder_level),
                    and_(Product.reorder_level.is_(None), Product.stock <= 10)
                )
            ))
            .limit(10)
        )
        
        low_stock_result = await db.execute(low_stock_query)
        low_stock_products = low_stock_result.scalars().all()
        
        low_stock_list = [
            LowStockProduct(
                product_id=p.id,
                name=p.name,
                slug=p.slug,
                stock_left=p.stock,
                reorder_level=p.reorder_level
            )
            for p in low_stock_products
        ]
        
        # Categories with product counts
        categories_query = (
            select(
                Category.id,
                Category.name,
                func.count(Product.id).label('product_count')
            )
            .outerjoin(Product)
            .group_by(Category.id, Category.name)
            .order_by(desc('product_count'))
        )
        
        categories_result = await db.execute(categories_query)
        categories = categories_result.fetchall()
        
        category_list = [
            CategorySummary(
                category_id=c.id,
                name=c.name,
                product_count=c.product_count or 0
            )
            for c in categories
        ]
        
        return ProductStats(
            total=total_products,
            active=active_products,
            inactive=inactive_products,
            out_of_stock=out_of_stock,
            low_stock_count=len(low_stock_list),
            low_stock_products=low_stock_list,
            categories=category_list
        )
    
    async def _get_user_stats(self, db: AsyncSession) -> UserStats:
        """Get user statistics"""
        
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=today_start.weekday())
        month_start = today_start.replace(day=1)
        thirty_days_ago = now - timedelta(days=30)
        
        total_users = await db.scalar(select(func.count(User.id))) or 0
        
        new_today = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= today_start)
        ) or 0
        
        new_this_week = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= week_start)
        ) or 0
        
        new_this_month = await db.scalar(
            select(func.count(User.id)).where(User.created_at >= month_start)
        ) or 0
        
        active_this_month = await db.scalar(
            select(func.count(func.distinct(Order.customer_id)))
            .where(Order.created_at >= thirty_days_ago)
        ) or 0
        
        verified_users = await db.scalar(
            select(func.count(User.id)).where(User.is_verified == True)
        ) or 0
        
        # Top buyers
        top_buyers = await self._get_top_buyers(db)
        
        return UserStats(
            total=total_users,
            new_today=new_today,
            new_this_week=new_this_week,
            new_this_month=new_this_month,
            active_this_month=active_this_month,
            verified_users=verified_users,
            top_buyers=top_buyers
        )
    
    async def _get_top_buyers(self, db: AsyncSession, limit: int = 5) -> List[TopBuyer]:
        """Get top buyers by total spent"""
        
        query = (
            select(
                User.id,
                User.first_name,
                User.last_name,
                User.email,
                func.coalesce(func.sum(Order.total), 0).label('total_spent'),
                func.count(Order.id).label('total_orders'),
                func.max(Order.created_at).label('last_order_date')
            )
            .select_from(User)
            .outerjoin(Order, User.id == Order.customer_id)
            .where(User.role == UserRole.CUSTOMER)
            .group_by(User.id, User.first_name, User.last_name, User.email)
            .having(func.count(Order.id) > 0)
            .order_by(desc('total_spent'))
            .limit(limit)
        )
        
        result = await db.execute(query)
        buyers = result.fetchall()
        
        return [
            TopBuyer(
                user_id=b.id,
                first_name=b.first_name,
                last_name=b.last_name,
                email=b.email,
                total_spent=b.total_spent or 0.0,
                total_orders=b.total_orders or 0,
                last_order_date=b.last_order_date
            )
            for b in buyers
        ]
    
    async def _get_order_stats(self, db: AsyncSession) -> OrderStats:
        """Get order statistics"""
        
        # Order counts by status
        status_counts = {}
        for status in OrderStatus:
            count = await db.scalar(
                select(func.count(Order.id)).where(Order.status == status)
            ) or 0
            status_counts[status.value.lower()] = count
        
        # Total order value
        total_value = await db.scalar(
            select(func.coalesce(func.sum(Order.total), 0))
        ) or 0.0
        
        # Latest orders
        latest_orders = await self._get_latest_orders(db)
        
        return OrderStats(
            pending=status_counts.get('pending', 0),
            confirmed=status_counts.get('confirmed', 0),
            shipped=status_counts.get('shipped', 0),
            delivered=status_counts.get('delivered', 0),
            cancelled=status_counts.get('cancelled', 0),
            returned=status_counts.get('returned', 0),
            total_value=total_value,
            latest_orders=latest_orders
        )
    
    async def _get_latest_orders(self, db: AsyncSession, limit: int = 10) -> List[LatestOrder]:
        """Get latest orders"""
        
        query = (
            select(Order, User)
            .join(User, Order.customer_id == User.id)
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        
        result = await db.execute(query)
        orders = result.fetchall()
        
        return [
            LatestOrder(
                order_id=order.Order.id,
                order_number=order.Order.order_number,
                user_name=f"{order.User.first_name} {order.User.last_name}",
                status=order.Order.status,
                total=order.Order.total,
                created_at=order.Order.created_at
            )
            for order in orders
        ]
    
    async def _get_review_stats(self, db: AsyncSession) -> ReviewStats:
        """Get review statistics"""
        
        total_reviews = await db.scalar(select(func.count(Review.id))) or 0
        
        avg_rating = await db.scalar(
            select(func.coalesce(func.avg(Review.rating), 0))
        ) or 0.0
        
        # Reviews this month
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reviews_this_month = await db.scalar(
            select(func.count(Review.id)).where(Review.created_at >= month_start)
        ) or 0
        
        # Pending reviews (not approved)
        pending_reviews = await db.scalar(
            select(func.count(Review.id)).where(Review.is_approved == False)
        ) or 0
        
        # Recent reviews
        recent_reviews = await self._get_recent_reviews(db)
        
        return ReviewStats(
            total_reviews=total_reviews,
            average_rating=round(avg_rating, 1),
            reviews_this_month=reviews_this_month,
            pending_reviews=pending_reviews,
            recent_reviews=recent_reviews
        )
    
    async def _get_recent_reviews(self, db: AsyncSession, limit: int = 5) -> List[RecentReview]:
        """Get recent reviews"""
        
        query = (
            select(Review, User, Product)
            .join(User, Review.user_id == User.id)
            .join(Product, Review.product_id == Product.id)
            .order_by(desc(Review.created_at))
            .limit(limit)
        )
        
        result = await db.execute(query)
        reviews = result.fetchall()
        
        return [
            RecentReview(
                review_id=review.Review.id,
                user_name=f"{review.User.first_name} {review.User.last_name}",
                product_name=review.Product.name,
                rating=review.Review.rating,
                comment=review.Review.comment[:100] + "..." if review.Review.comment and len(review.Review.comment) > 100 else review.Review.comment or "",
                created_at=review.Review.created_at
            )
            for review in reviews
        ]
    
    async def _get_revenue_by_category(self, db: AsyncSession) -> List[RevenueByCategoryItem]:
        """Get revenue breakdown by category"""
        
        query = (
            select(
                Category.id,
                Category.name,
                func.coalesce(func.sum(OrderItem.quantity * OrderItem.price), 0).label('revenue'),
                func.count(func.distinct(Order.id)).label('order_count')
            )
            .select_from(Category)
            .outerjoin(Product)
            .outerjoin(OrderItem)
            .outerjoin(Order)
            .where(Order.status == OrderStatus.DELIVERED)
            .group_by(Category.id, Category.name)
            .order_by(desc('revenue'))
        )
        
        result = await db.execute(query)
        categories = result.fetchall()
        
        return [
            RevenueByCategoryItem(
                category_id=c.id,
                category_name=c.name,
                revenue=c.revenue or 0.0,
                order_count=c.order_count or 0
            )
            for c in categories
        ]
    
    async def _get_system_alerts(self, db: AsyncSession) -> SystemAlerts:
        """Get system alerts for admin attention"""
        
        low_stock = await db.scalar(
            select(func.count(Product.id))
            .where(and_(
                Product.stock > 0,
                or_(
                    and_(Product.reorder_level.is_not(None), Product.stock <= Product.reorder_level),
                    and_(Product.reorder_level.is_(None), Product.stock <= 10)
                )
            ))
        ) or 0
        
        out_of_stock = await db.scalar(
            select(func.count(Product.id)).where(Product.stock == 0)
        ) or 0
        
        pending_orders = await db.scalar(
            select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING)
        ) or 0
        
        unread_reviews = await db.scalar(
            select(func.count(Review.id)).where(Review.is_approved == False)
        ) or 0
        
        # Failed payments (assuming we track payment failures)
        failed_payments = await db.scalar(
            select(func.count(PaymentTransaction.id))
            .where(PaymentTransaction.status == PaymentStatus.FAILED)
        ) or 0
        
        return SystemAlerts(
            low_stock_products=low_stock,
            out_of_stock_products=out_of_stock,
            pending_orders=pending_orders,
            unread_reviews=unread_reviews,
            failed_payments=failed_payments
        )


# Create service instance
dashboard_service = DashboardService()
