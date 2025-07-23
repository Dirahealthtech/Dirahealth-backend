from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, func, desc, and_
from typing import List, Optional, Tuple
from uuid import uuid4

from ..models import Product, Category, User
from ..enums import UserRole
from ..schemas.product import ProductCreate, ProductUpdate
from ..schemas.category import CategoryUpdate
from ..exceptions import NotFoundException, ConflictException, BadRequestException

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
        Create a new product with structured data and transaction management
        """
        try:
            # Check if category exists
            await self.check_category_exists(product_data.category_id, db)
            
            # Check if SKU already exists
            sku_exists = await self.check_sku_exists(product_data.inventory.sku, None, db)
            if sku_exists:
                raise ConflictException(f"Product with SKU {product_data.inventory.sku} already exists")
            
            # Generate unique slug
            slug = await self.generate_unique_slug(product_data.name, None, db)
            
            # Extract data from structured format
            pricing = product_data.pricing
            inventory = product_data.inventory
            shipping = product_data.shipping
            warranty = product_data.warranty
            metadata = product_data.metadata
            
            # Handle dimensions
            dimensions_data = None
            if shipping and shipping.dimensions:
                dimensions_data = {
                    "length": shipping.dimensions.length,
                    "width": shipping.dimensions.width,
                    "height": shipping.dimensions.height,
                    "unit": shipping.dimensions.unit
                }
            
            # Create new product with structured data
            new_product = Product(
                name=product_data.name,
                slug=slug,
                description=product_data.description,  # Already sanitized by validator
                category_id=product_data.category_id,
                supplier_id=product_data.supplier_id,
                
                # Pricing fields
                price=pricing.price,
                discounted_price=pricing.discounted_price,
                tax_rate=pricing.tax_rate,
                
                # Inventory fields
                sku=inventory.sku,
                stock=inventory.stock,
                reorder_level=inventory.reorder_level,
                requires_prescription=inventory.requires_prescription,
                is_active=inventory.is_active,
                
                # Images
                images=product_data.images,
                
                # Shipping fields
                weight=shipping.weight if shipping else None,
                dimensions=dimensions_data,
                
                # Warranty fields
                warranty_period=warranty.period if warranty else None,
                warranty_unit=warranty.unit if warranty else None,
                warranty_description=warranty.description if warranty else None,
                
                # Metadata fields
                specifications=metadata.specifications if metadata else None,
                tags=metadata.tags if metadata else None,
            )
            
            db.add(new_product)
            await db.commit()
            await db.refresh(new_product)
            
            return new_product
            
        except ConflictException:
            raise
        except NotFoundException:
            raise
        except Exception as e:
            await db.rollback()
            print(f"Error creating product: {e}")
            raise BadRequestException(f"Failed to create product: {str(e)}")

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
            print(f"Error listing products: {e}")
            return [], 0
    
    async def update_product(self, product_id: int, product_data: ProductUpdate, db: AsyncSession) -> Product:
        """
        Update a product with structured data
        """
        try:
            # Check if product exists
            product = await self.get_product_by_id(product_id, db)
            
            # Check if category exists if changing category
            if product_data.category_id is not None:
                await self.check_category_exists(product_data.category_id, db)
            
            # Check if SKU exists if changing SKU (from inventory structure)
            if (product_data.inventory and 
                product_data.inventory.sku is not None and 
                product_data.inventory.sku != product.sku):
                sku_exists = await self.check_sku_exists(product_data.inventory.sku, product_id, db)
                if sku_exists:
                    raise ConflictException(f"Product with SKU {product_data.inventory.sku} already exists")
            
            # Build update dictionary from structured data
            update_data = {}
            
            # Basic fields
            if product_data.name is not None:
                update_data["name"] = product_data.name
                # Generate new slug if name is updated
                new_slug = await self.generate_unique_slug(product_data.name, product_id, db)
                update_data["slug"] = new_slug
            
            if product_data.description is not None:
                update_data["description"] = product_data.description  # Already sanitized by validator
            
            if product_data.category_id is not None:
                update_data["category_id"] = product_data.category_id
            
            if product_data.supplier_id is not None:
                # Handle supplier_id = 0 as None (no supplier)
                update_data["supplier_id"] = None if product_data.supplier_id == 0 else product_data.supplier_id
            
            if product_data.images is not None:
                update_data["images"] = product_data.images
            
            # Pricing data
            if product_data.pricing:
                if product_data.pricing.price is not None:
                    update_data["price"] = product_data.pricing.price
                if product_data.pricing.discounted_price is not None:
                    update_data["discounted_price"] = product_data.pricing.discounted_price
                if product_data.pricing.tax_rate is not None:
                    update_data["tax_rate"] = product_data.pricing.tax_rate
            
            # Inventory data
            if product_data.inventory:
                if product_data.inventory.sku is not None:
                    update_data["sku"] = product_data.inventory.sku
                if product_data.inventory.stock is not None:
                    update_data["stock"] = product_data.inventory.stock
                if product_data.inventory.reorder_level is not None:
                    update_data["reorder_level"] = product_data.inventory.reorder_level
                if product_data.inventory.requires_prescription is not None:
                    update_data["requires_prescription"] = product_data.inventory.requires_prescription
                if product_data.inventory.is_active is not None:
                    update_data["is_active"] = product_data.inventory.is_active
            
            # Shipping data
            if product_data.shipping:
                if product_data.shipping.weight is not None:
                    update_data["weight"] = product_data.shipping.weight
                if product_data.shipping.dimensions is not None:
                    dimensions_data = {
                        "length": product_data.shipping.dimensions.length,
                        "width": product_data.shipping.dimensions.width,
                        "height": product_data.shipping.dimensions.height,
                        "unit": product_data.shipping.dimensions.unit
                    }
                    update_data["dimensions"] = dimensions_data
            
            # Warranty data
            if product_data.warranty:
                if product_data.warranty.period is not None:
                    update_data["warranty_period"] = product_data.warranty.period
                if product_data.warranty.unit is not None:
                    update_data["warranty_unit"] = product_data.warranty.unit
                if product_data.warranty.description is not None:
                    update_data["warranty_description"] = product_data.warranty.description
            
            # Metadata
            if product_data.metadata:
                if product_data.metadata.specifications is not None:
                    update_data["specifications"] = product_data.metadata.specifications
                if product_data.metadata.tags is not None:
                    update_data["tags"] = product_data.metadata.tags
            
            # Only update if there are fields to update
            if update_data:
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

    # Category management methods
    async def get_category_by_id(self, category_id: int, db: AsyncSession) -> Category:
        """
        Get a category by its ID
        """
        query = select(Category).where(Category.id == category_id)
        result = await db.execute(query)
        category = result.scalars().first()
        
        if not category:
            raise NotFoundException(f"Category with ID {category_id} not found")
        
        return category

    async def check_category_slug_exists(self, slug: str, category_id: Optional[int], db: AsyncSession) -> bool:
        """
        Check if a category slug already exists
        """
        query = select(Category).where(Category.slug == slug)
        
        # If updating existing category, exclude current category from check
        if category_id is not None:
            query = query.where(Category.id != category_id)
        
        result = await db.execute(query)
        existing = result.scalars().first()
        
        return existing is not None

    async def generate_category_slug(self, name: str, category_id: Optional[int], db: AsyncSession) -> str:
        """
        Generate a unique slug from a category name
        """
        # Create base slug
        slug = name.lower().replace(" ", "-").replace("_", "-")
        
        # Remove special characters and multiple dashes
        import re
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        # Check if slug already exists
        slug_exists = await self.check_category_slug_exists(slug, category_id, db)
        
        if slug_exists:
            # Add random suffix to make slug unique
            slug = f"{slug}-{uuid4().hex[:6]}"
        
        return slug

    async def update_category(self, category_id: int, category_data: CategoryUpdate, db: AsyncSession) -> Category:
        """
        Update a category
        """
        try:
            # Check if category exists
            category = await self.get_category_by_id(category_id, db)
            
            # Check if parent category exists if changing parent
            if category_data.parent_id is not None:
                # Prevent setting category as its own parent
                if category_data.parent_id == category_id:
                    raise ConflictException("Category cannot be its own parent")
                
                # Check if parent category exists
                await self.get_category_by_id(category_data.parent_id, db)
            
            # Update category with non-None fields
            update_data = category_data.model_dump(exclude_unset=True, exclude_none=True)
            
            # If name is updated, update slug too
            if "name" in update_data:
                new_slug = await self.generate_category_slug(update_data["name"], category_id, db)
                update_data["slug"] = new_slug
            
            # Update the category
            stmt = (
                update(Category)
                .where(Category.id == category_id)
                .values(**update_data)
                .execution_options(synchronize_session="fetch")
            )
            
            await db.execute(stmt)
            await db.commit()
            
            # Refresh category object
            refreshed = await db.execute(select(Category).where(Category.id == category_id))
            updated_category = refreshed.scalars().first()
            
            return updated_category
        except Exception as e:
            await db.rollback()
            raise

    async def delete_category(self, category_id: int, db: AsyncSession) -> bool:
        """
        Delete a category
        Returns True if successful
        """
        try:
            # Check if category exists
            category = await self.get_category_by_id(category_id, db)
            
            # Check if category has any products
            products_query = select(func.count()).select_from(Product).where(Product.category_id == category_id)
            products_result = await db.execute(products_query)
            products_count = products_result.scalar()
            
            if products_count > 0:
                raise ConflictException(f"Cannot delete category. It has {products_count} associated products. Please reassign or delete the products first.")
            
            # Check if category has any child categories
            children_query = select(func.count()).select_from(Category).where(Category.parent_id == category_id)
            children_result = await db.execute(children_query)
            children_count = children_result.scalar()
            
            if children_count > 0:
                raise ConflictException(f"Cannot delete category. It has {children_count} child categories. Please reassign or delete the child categories first.")
            
            # Delete the category
            stmt = (
                delete(Category)
                .where(Category.id == category_id)
                .execution_options(synchronize_session="fetch")
            )
            
            await db.execute(stmt)
            await db.commit()
            
            return True
        except Exception as e:
            await db.rollback()
            raise