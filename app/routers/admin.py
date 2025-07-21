from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_, desc, func
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional

from ..core.dependencies import get_db, RoleChecker
from ..enums import UserRole
from ..models import Category, User
from ..schemas.product import (
    ProductCreate, 
    ProductResponse, 
    ProductUpdate,
    ProductListResponse
)
from ..schemas import CreateAdminUser
from ..services.admin_service import AdminService
from ..services import AuthService
from ..exceptions import NotFoundException, BadRequestException, ConflictException
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()

admin_only = Depends(RoleChecker([UserRole.ADMIN]))
admin_service = AdminService()
auth_service = AuthService()


# Setting up initial admin user
@router.post("/setup-initial-admin", status_code=status.HTTP_201_CREATED)
async def setup_initial_admin(user_data: CreateAdminUser, db: AsyncSession = Depends(get_db)):
    """
    Creates the first admin user for the system. This endpoint should only be used during initial setup
    and should be secured or disabled in production.

    - **user_data**: Admin user creation data including name, email, and password
    """
    try:
        # Check if any admin user already exists
        admin_query = select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
        result = await db.execute(admin_query)
        admin_count = result.scalar()
        
        print(f"Current admin count: {admin_count}")
        
        # Only allow creation if no admin exists
        if admin_count > 0:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Admin already exists. This endpoint is for initial setup only."}
            )
        try:
            # Create first admin user
            new_user = await auth_service.create_admin_user(user_data, UserRole.ADMIN, db)
            
            print(f"Admin user created successfully: {new_user.email}")
            
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "message": "Initial admin user created successfully",
                    "user_id": new_user.id,
                    "email": new_user.email,
                    "role": new_user.role
                }
            )
        except Exception as inner_e:
            print(f"Error in auth_service.create_admin_user: {str(inner_e)}")
            raise
            
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to create admin: {str(e)}"}
        )


# User role creation and management
@router.post("/users", dependencies=[admin_only], status_code=status.HTTP_201_CREATED)
async def create_admin_user(user_data: CreateAdminUser, role: UserRole, db: AsyncSession = Depends(get_db)):
    """
    **Create New User with Specified Role**
    
    Creates a new user account with admin-specified role. Only accessible by admin users.
    
    **Args:**

    - **user_data**: User creation data (name, email, password)
    - **role**: User role to assign (admin, customer, etc.)
    """
    user_data_dict = user_data.model_dump()
    user_data_dict["role"] = role
    
    # Create user with the specified role
    new_user = await auth_service.create_admin_user(user_data, role, db)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": f"User with {role.value} role created successfully",
            "user_id": new_user.id,
            "email": new_user.email,
            "role": new_user.role
        }
    )

@router.patch("/users/{user_id}/role", status_code=status.HTTP_200_OK)
async def update_user_role(
    user_id: int, 
    role: UserRole,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **Update User Role**
    
    Updates an existing user's role. Only accessible by admin users.
    
    **Args:**

    - **user_id**: ID of the user to update
    - **role**: New role to assign to the user
    """
    try:
        updated_user = await admin_service.update_user_role(user_id, role, db)
        
        return {
            "message": f"User role updated to {role.value} successfully",
            "user_id": updated_user.id,
            "email": updated_user.email,
            "role": updated_user.role
        }
    except NotFoundException as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(e.detail)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to update user role: {str(e)}"}
        )

# Category operations
@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Create New Category**
    
    Creates a new product category. Categories are used to organize products into logical groups.
    
    **Args:**

    - **category_data**: Category creation data including name, description, parent_id, and image
        
    **Returns:**
    - Created category details with generated slug and ID
        
    **Features:**
    - Auto-generates URL-friendly slug from category name
    - Supports hierarchical categories with parent_id
    - Optional image URL for category display
    """
    try:
        # Create a category
        new_category = Category(
            name=category_data.name,
            slug=category_data.name.lower().replace(" ", "-"),
            description=category_data.description,
            parent_id=category_data.parent_id,
            image=category_data.image,
            is_active=True
        )
        
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        
        return new_category
    except Exception as e:
        raise BadRequestException(f"Failed to create category: {str(e)}")

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    **List All Categories**
    
    Retrieves a paginated list of all product categories. Accessible by all authenticated users.
    
    **Query Parameters:**

    - **skip**: Number of categories to skip (for pagination) - Default: 0
    - **limit**: Maximum number of categories to return - Default: 100, Max: 100
    """
    query = select(Category).offset(skip).limit(limit)
    result = await db.execute(query)
    categories = result.scalars().all()
    return categories
 
@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Update Category**
    
    Updates an existing category's information. Supports partial updates with automatic slug generation.
    
    **Path Parameters:**

    - **category_id**: ID of the category to update
        
    **Request Body:**

    - **name**: Update category name (optional)
    - **description**: Update category description (optional)
    - **parent_id**: Update parent category (optional, use null for root category)
    - **image**: Update category image (optional)
    - **is_active**: Update category status (optional)
    """
    try:
        updated_category = await admin_service.update_category(category_id, category_data, db)
        return updated_category
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to update category: {str(e)}")

@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Delete Category**
    
    Deletes a category if it has no associated products or child categories.
    
    **Path Parameters:**

    - **category_id**: ID of the category to delete
        
    **Returns:**
    - Success message confirming deletion
    """
    try:
        await admin_service.delete_category(category_id, db)
        return {"message": f"Category {category_id} deleted successfully"}
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to delete category: {str(e)}")
        
@router.post("/products", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **Create New Product**
    
    Creates a new product in the healthcare inventory system. Handles comprehensive product data
    including pricing, inventory, specifications, and image management.
    
    **Request Body Fields:**

    - **name**: Product name (required)
    - **description**: Detailed product description (required)
    - **category_id**: ID of the product category (required)
    - **sku**: Stock Keeping Unit - unique identifier (required)
    - **price**: Base price of the product (required)
    - **stock**: Current stock quantity (required)
    - **discounted_price**: Sale price (optional)
    - **tax_rate**: Tax percentage (optional)
    - **requires_prescription**: Whether prescription is needed (default: false)
    - **is_active**: Product availability status (default: true)
    - **supplier_id**: Associated supplier ID (optional)
    - **images**: Comma-separated images (optional)
    - **weight**: Product weight (optional)
    - **dimensions**: Product dimensions as JSON (optional)
    - **specifications**: Technical specifications as JSON (optional)
    - **tags**: Product tags as JSON array (optional)
    - **reorder_level**: Minimum stock for reorder alerts (optional)
    - **warranty_period**: Warranty duration (optional)
    - **warranty_unit**: Warranty time unit (months/years) (optional)
    - **warranty_description**: Warranty details (optional)
        
    **Returns:**

    - Created product with generated ID and slug
        
    **Raises:**
    - **403**: If not admin user
    - **404**: If category doesn't exist
    - **409**: If SKU already exists
    - **400**: If validation fails or creation errors
    """
    try:
        new_product = await admin_service.create_product(product_data, db)
        return new_product
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to create product: {str(e)}")


@router.get("/products", response_model=ProductListResponse)
async def list_products(
    skip: int = 0,
    limit: int = 20,
    name: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    requires_prescription: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **List Products with Advanced Filtering**
    
    Retrieves a paginated and filtered list of products with comprehensive search and sorting capabilities.
    
    **Query Parameters:**

    - **skip**: Number of products to skip for pagination (default: 0)
    - **limit**: Maximum products to return (default: 20, max: 100)
    - **name**: Filter by product name (partial match, case-insensitive)
    - **category_id**: Filter by specific category ID
    - **is_active**: Filter by product status (true/false)
    - **requires_prescription**: Filter by prescription requirement (true/false)
    - **sort_by**: Field to sort by (id, name, price, stock, created_at, etc.)
    - **sort_order**: Sort direction (asc/desc, default: asc)
        
    **Returns:**

    - Paginated product list with metadata:
        - **items**: Array of product objects
        - **total**: Total number of matching products
        - **page**: Current page number
        - **size**: Items per page
        - **pages**: Total number of pages
    """
    try:
        products, total_count = await admin_service.list_products(
            skip=skip,
            limit=limit,
            name=name,
            category_id=category_id,
            is_active=is_active,
            requires_prescription=requires_prescription,
            sort_by=sort_by,
            sort_order=sort_order,
            db=db
        )
        
        return {
            "items": products,
            "total": total_count,
            "page": skip // limit + 1 if limit > 0 else 1,
            "size": limit,
            "pages": (total_count + limit - 1) // limit if limit > 0 else 1
        }
    except Exception as e:
        # Return empty results instead of error
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "size": limit,
            "pages": 0
        }


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **Get Product Details**
    
    Retrieves comprehensive details for a specific product by its ID.
    
    **Path Parameters:**

    - **product_id**: Unique identifier of the product
    """
    try:
        product = await admin_service.get_product_by_id(product_id, db)
        return product
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to retrieve product: {str(e)}")


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **Update Product**
    
    Updates an existing product with partial data. Supports updating any product field while
    maintaining data integrity and business rules.
    
    **Path Parameters:**

    - **product_id**: ID of the product to update
        
    **Request Body:** (All fields optional for partial updates)

    - **name**: Update product name
    - **description**: Update product description
    - **category_id**: Change product category
    - **sku**: Update SKU (must remain unique)
    - **price**: Update base price
    - **discounted_price**: Update sale price
    - **tax_rate**: Update tax percentage
    - **stock**: Update stock quantity
    - **images**: Update images (comma-separated)
    - **requires_prescription**: Update prescription requirement
    - **is_active**: Update product status
    - **supplier_id**: Change associated supplier
    - **weight**: Update product weight
    - **dimensions**: Update product dimensions
    - **specifications**: Update technical specifications
    - **tags**: Update product tags
    - **reorder_level**: Update reorder threshold
    - **warranty_period**: Update warranty duration
    - **warranty_unit**: Update warranty time unit
    - **warranty_description**: Update warranty details
    """
    try:
        updated_product = await admin_service.update_product(product_id, product_data, db)
        return updated_product
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to update product: {str(e)}")


@router.delete("/products/{product_id}", status_code=status.HTTP_200_OK)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Delete a product - Admin only
    """
    try:
        await admin_service.delete_product(product_id, db)
        return {"message": f"Product {product_id} deleted successfully"}
    except NotFoundException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to delete product: {str(e)}")


# Batch operations
@router.patch("/products/batch/update-status", status_code=status.HTTP_200_OK)
async def batch_update_product_status(
    product_ids: List[int] = Query(...),
    is_active: bool = Query(...),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Update status for multiple products at once - Admin only
    """
    try:
        updated_count = await admin_service.batch_update_product_status(product_ids, is_active, db)
        
        return {
            "message": f"Updated status for {updated_count} products",
            "updated_count": updated_count
        }
    except Exception as e:
        raise BadRequestException(f"Failed to update products: {str(e)}")


@router.delete("/batch-products", status_code=status.HTTP_200_OK)
async def batch_delete_products(
    product_ids: List[int] = Query(...),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Delete multiple products at once - Admin only
    """
    try:
        deleted_count = await admin_service.batch_delete_products(product_ids, db)
        
        return {
            "message": f"Deleted {deleted_count} products",
            "deleted_count": deleted_count
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Failed to delete products: {str(e)}"}
        )

