from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func, desc, and_
from typing import List, Optional, Dict, Any, Tuple
from uuid import uuid4

from ..models import Product, Category, User
from ..enums import UserRole, ProductType
from ..schemas.product import ProductCreate, ProductUpdate
from ..exceptions import NotFoundException, BadRequestException, ConflictException

class AdminService:
    async def generate_unique_slug(self, name: str, product_id: Optional[int], db: AsyncSession) -> str:
        """
        Generate a unique slug from a product name
        """
        # Create base slug
        slug = name.lower().replace(" ", "-")
        
        # Check if slug already exists
        query = select(Product).where(Product.slug == slug)
        
        # If updating existing product, exclude current product from check
        if product_id is not None:
            query = query.where(Product.id != product_id)
        
        result = await db.execute(query)
        existing = result.scalars().first()
        
        if existing:
            # Add random suffix to make slug unique
            slug = f"{slug}-{uuid4().hex[:6]}"
        
        return slug
    
    async def check_sku_exists(self, sku: str, product_id: Optional[int], db: AsyncSession) -> bool:
        """
        Check if a SKU already exists
        """
        query = select(Product).where(Product.sku == sku)
        
        # If updating existing product, exclude current product from check
        if product_id is not None:
            query = query.where(Product.id != product_id)
        
        result = await db.execute(query)
        existing = result.scalars().first()
        
        return existing is not None
    
    async def create_product(self, product_data: ProductCreate, db: AsyncSession) -> Product:
        """
        Create a new product with transaction management
        """
        try:
            # Check if category exists
            await self.check_category_exists(product_data.category_id, db)
            
            # Check if SKU already exists
            sku_exists = await self.check_sku_exists(product_data.sku, None, db)
            if sku_exists:
                raise ConflictException(f"Product with SKU {product_data.sku} already exists")
            
            # Generate unique slug
            slug = await self.generate_unique_slug(product_data.name, None, db)
            
            # Handle images
            images_data = None
            if hasattr(product_data, 'images') and product_data.images:
                images_data = product_data.images
            elif hasattr(product_data, 'image_url') and product_data.image_url:
                images_data = [{"url": product_data.image_url, "isMain": True}]
            
            # Create new product
            new_product = Product(
                name=product_data.name,
                slug=slug,
                description=product_data.description,
                category_id=product_data.category_id,
                product_type=product_data.product_type,
                sku=product_data.sku,
                price=product_data.price,
                discounted_price=product_data.discounted_price,
                tax_rate=product_data.tax_rate,
                stock=product_data.stock,
                requires_prescription=product_data.requires_prescription,
                is_active=product_data.is_active,
                supplier_id=product_data.supplier_id,
                images=images_data,
                weight=product_data.weight if hasattr(product_data, 'weight') else None,
                dimensions=product_data.dimensions if hasattr(product_data, 'dimensions') else None,
                specifications=product_data.specifications if hasattr(product_data, 'specifications') else None,
                tags=product_data.tags if hasattr(product_data, 'tags') else None,
                reorder_level=product_data.reorder_level if hasattr(product_data, 'reorder_level') else None,
                warranty_period=product_data.warranty_period if hasattr(product_data, 'warranty_period') else None,
                warranty_unit=product_data.warranty_unit if hasattr(product_data, 'warranty_unit') else None,
                warranty_description=product_data.warranty_description if hasattr(product_data, 'warranty_description') else None
            )
            
            db.add(new_product)
            await db.commit()
            await db.refresh(new_product)
            
            return new_product
        except Exception as e:
            await db.rollback()
            raise

    async def get_product_by_id(self, product_id: int, db: AsyncSession) -> Product:
        """
        Get a product by its ID
        """
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        product = result.scalars().first()
        
        if not product:
            raise NotFoundException(f"Product with ID {product_id} not found")
        
        return product
    
    async def check_category_exists(self, category_id: int, db: AsyncSession) -> Category:
        """
        Check if a category exists by its ID
        """
        category_stmt = select(Category).where(Category.id == category_id)
        result = await db.execute(category_stmt)
        category = result.scalars().first()
        
        if not category:
            raise NotFoundException(f"Category with ID {category_id} not found")
        
        return category
    
    async def list_products(
        self, 
        skip: int, 
        limit: int,
        name: Optional[str] = None,
        category_id: Optional[int] = None,
        product_type: Optional[ProductType] = None,
        is_active: Optional[bool] = None,
        requires_prescription: Optional[bool] = None,
        sort_by: str = "id",
        sort_order: str = "asc",
        db: AsyncSession = None
    ) -> Tuple[List[Product], int]:
        """
        List products with filters, sorting and pagination
        Returns products and total count
        """
        try:
            # Start with base query
            query = select(Product)
            
            # Apply filters
            if name:
                query = query.where(Product.name.ilike(f"%{name}%"))
            if category_id:
                query = query.where(Product.category_id == category_id)
            if product_type:
                query = query.where(Product.product_type == product_type)
            if is_active is not None:
                query = query.where(Product.is_active == is_active)
            if requires_prescription is not None:
                query = query.where(Product.requires_prescription == requires_prescription)
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(Product)
            # Apply the same filters to count query
            if name:
                count_query = count_query.where(Product.name.ilike(f"%{name}%"))
            if category_id:
                count_query = count_query.where(Product.category_id == category_id)
            if product_type:
                count_query = count_query.where(Product.product_type == product_type)
            if is_active is not None:
                count_query = count_query.where(Product.is_active == is_active)
            if requires_prescription is not None:
                count_query = count_query.where(Product.requires_prescription == requires_prescription)
                
            total_count_result = await db.execute(count_query)
            total_count = total_count_result.scalar() or 0
            
            # Apply sorting
            if hasattr(Product, sort_by):
                if sort_order.lower() == "desc":
                    query = query.order_by(desc(getattr(Product, sort_by)))
                else:
                    query = query.order_by(getattr(Product, sort_by))
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            products = result.scalars().all()
            
            return products, total_count
        except Exception as e:
            # TODO: REMOVE DEBUGGING STEP
            print(f"Error listing products: {e}")
            return [], 0
    
    async def update_product(self, product_id: int, product_data: ProductUpdate, db: AsyncSession) -> Product:
        """
        Update a product
        """
        try:
            # Check if product exists
            product = await self.get_product_by_id(product_id, db)
            
            # Check if category exists if changing category
            if product_data.category_id is not None:
                await self.check_category_exists(product_data.category_id, db)
            
            # Check if SKU exists if changing SKU
            if product_data.sku is not None and product_data.sku != product.sku:
                sku_exists = await self.check_sku_exists(product_data.sku, product_id, db)
                if sku_exists:
                    raise ConflictException(f"Product with SKU {product_data.sku} already exists")
            
            # Update product with non-None fields
            update_data = product_data.model_dump(exclude_unset=True, exclude_none=True)
            
            # If name is updated, update slug too
            if "name" in update_data:
                new_slug = await self.generate_unique_slug(update_data["name"], product_id, db)
                update_data["slug"] = new_slug
            
            # Update the product
            stmt = (
                update(Product)
                .where(Product.id == product_id)
                .values(**update_data)
                .execution_options(synchronize_session="fetch")
            )
            
            await db.execute(stmt)
            await db.commit()
            
            # Refresh product object
            refreshed = await db.execute(select(Product).where(Product.id == product_id))
            updated_product = refreshed.scalars().first()
            
            return updated_product
        except Exception as e:
            await db.rollback()
            raise
    
    async def delete_product(self, product_id: int, db: AsyncSession) -> bool:
        """
        Delete a product
        Returns True if successful
        """
        try:
            # Check if product exists
            product = await self.get_product_by_id(product_id, db)
            
            # Delete the product
            stmt = (
                delete(Product)
                .where(Product.id == product_id)
                .execution_options(synchronize_session="fetch")
            )
            
            await db.execute(stmt)
            await db.commit()
            
            return True
        except Exception as e:
            await db.rollback()
            raise
    
    async def update_product_image(self, product_id: int, image_url: str, db: AsyncSession) -> Product:
        """
        Update a product's image URL
        """
        try:
            # Check if product exists
            product = await self.get_product_by_id(product_id, db)
            
            # Handle the images JSON structure
            if product.images is None:
                # Create a new images array with this as the main image
                images = [{"url": image_url, "isMain": True}]
            else:
                # Add to existing images
                images = product.images
                has_main = any(img.get("isMain") for img in images)
                images.append({"url": image_url, "isMain": not has_main})
            
            # Update the product's images field
            stmt = (
                update(Product)
                .where(Product.id == product_id)
                .values(images=images)  # Use images, not image_url
                .execution_options(synchronize_session="fetch")
            )
            
            await db.execute(stmt)
            await db.commit()
            
            # Refresh product object
            refreshed = await db.execute(select(Product).where(Product.id == product_id))
            updated_product = refreshed.scalars().first()
            
            return updated_product
        except Exception as e:
            await db.rollback()
            raise
    
    async def batch_update_product_status(
        self, 
        product_ids: List[int], 
        is_active: bool, 
        db: AsyncSession
    ) -> int:
        """
        Update status for multiple products
        Returns count of updated rows
        """
        try:
            # Update products
            stmt = (
                update(Product)
                .where(Product.id.in_(product_ids))
                .values(is_active=is_active)
                .execution_options(synchronize_session="fetch")
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            return result.rowcount
        except Exception as e:
            await db.rollback()
            raise
    
    async def batch_delete_products(self, product_ids: List[int], db: AsyncSession) -> int:
        """
        Delete multiple products
        Returns count of deleted rows
        """
        try:
            # Delete products
            stmt = (
                delete(Product)
                .where(Product.id.in_(product_ids))
                .execution_options(synchronize_session="fetch")
            )
            
            result = await db.execute(stmt)
            await db.commit()
            
            return result.rowcount
        except Exception as e:
            await db.rollback()
            raise
    
    async def get_user_by_id(self, user_id: int, db: AsyncSession) -> User:
        """
        Get a user by ID
        """
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")
        
        return user
    
    async def update_user_role(self, user_id: int, role: UserRole, db: AsyncSession) -> User:
        """
        Update a user's role
        """
        try:
            # Check if user exists
            user = await self.get_user_by_id(user_id, db)
            
            # Update role
            user.role = role
            await db.commit()
            await db.refresh(user)
            
            return user
        except Exception as e:
            await db.rollback()
            raise