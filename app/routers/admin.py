from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_, desc, func
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional
import json

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
from ..services.file_service import FileService
from ..exceptions import NotFoundException, BadRequestException, ConflictException
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()

admin_only = Depends(RoleChecker([UserRole.ADMIN]))
admin_service = AdminService()
auth_service = AuthService()
file_service = FileService()


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
    name: str = Form(...),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """    
    Creates a new product category
    
    #### Form Fields:
    - **name**: Category name (required)
    - **description**: Category description (optional)
    - **parent_id**: Parent category ID for hierarchical structure (optional)
        
    #### File Upload:**
    - **image**: Category image file (optional)
    - **Formats**: JPG, JPEG, PNG, GIF, WebP
    - **Size**: Maximum 5MB
        
    **Returns:**
    - Created category details with generated slug and ID
    """
    try:
        # Handle image upload if provided
        image_path = None
        if image and image.filename:
            image_path = await file_service.save_image(image, "categories")
        
        # Create a category
        new_category = Category(
            name=name,
            slug=name.lower().replace(" ", "-"),
            description=description,
            parent_id=parent_id,
            image=image_path,
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
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    parent_id: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Update Category**
    
    Updates an existing category's information, Supports partial updates
    
    **Path Parameters:**
    - **category_id**: ID of the category to update
        
    **Form Fields:** (All optional for partial updates)
    - **name**: Update category name
    - **description**: Update category description
    - **parent_id**: Update parent category (use null for root category)
    - **is_active**: Update category status
        
    **File Upload:**
    - **image**: New category image file (optional)
    - **Formats**: JPG, JPEG, PNG, GIF, WebP
    - **Size**: Maximum 5MB
    """
    try:
        # Handle image upload if provided
        image_path = None
        if image and image.filename:
            image_path = await file_service.save_image(image, "categories")
        
        # Build update data
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if parent_id is not None:
            update_data["parent_id"] = parent_id
        if is_active is not None:
            update_data["is_active"] = is_active
        if image_path:
            update_data["image"] = image_path
        
        # Create CategoryUpdate object
        category_update = CategoryUpdate(**update_data)
        
        updated_category = await admin_service.update_category(category_id, category_update, db)
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
    name: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(...),
    stock: int = Form(...),
    sku: str = Form(None),
    discounted_price: Optional[float] = Form(0.0),
    tax_rate: Optional[float] = Form(0.0),
    requires_prescription: bool = Form(False),
    is_active: bool = Form(True),
    supplier_id: Optional[int] = Form(None),
    weight: Optional[float] = Form(None),
    reorder_level: Optional[int] = Form(None),
    warranty_period: Optional[int] = Form(None),
    warranty_unit: Optional[str] = Form(None),
    warranty_description: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),  # JSON string
    dimensions: Optional[str] = Form(None),  # JSON string
    tags: Optional[str] = Form(None),  # Comma-separated string
    images: List[UploadFile] = File([]),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    **Create New Product with Images**
    
    Creates a new product in the healthcare inventory system with automatic image upload handling.
    
    #### Form Fields:
    - **name**: Product name (required)
    - **description**: Detailed product description (required)
    - **category_id**: ID of the product category (required)
    - **price**: Base price of the product (required)
    - **stock**: Current stock quantity (required)
    - **sku**: Stock Keeping Unit - unique identifier (Optional)
    - **discounted_price**: Sale price (optional)
    - **tax_rate**: Tax percentage (optional)
    - **requires_prescription**: Whether prescription is needed (default: false)
    - **is_active**: Product availability status (default: true)
    - **supplier_id**: Associated supplier ID (optional)
    - **weight**: Product weight (optional)
    - **reorder_level**: Minimum stock for reorder alerts (optional)
    - **warranty_period**: Warranty duration (optional)
    - **warranty_unit**: Warranty time unit (months/years) (optional)
    - **warranty_description**: Warranty details (optional)
    - **specifications**: Technical specifications as JSON string (optional)
    - **dimensions**: Product dimensions as JSON string (optional)
    - **tags**: Product tags as comma-separated string (optional)
        
    **File Uploads:**
    - **images**: Multiple product image files (optional)
    - **Formats**: JPG, JPEG, PNG, GIF, WebP
    - **Size**: Maximum 5MB per file
    - **Count**: Maximum 10 files
    
    **Returns:**
    - Created product with generated ID, slug, and comma seperated image URLs
    """
    try:
        # Validate image count
        if len(images) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 images allowed per product"
            )
        
        # Handle image uploads
        image_paths = []
        for image in images:
            if image.filename:  # Only process files with names
                image_path = await file_service.save_image(image, "products")
                image_paths.append(image_path)
        
        # Parse JSON fields if provided
        specifications_dict = None
        if specifications and specifications.strip():
            try:
                specifications_dict = json.loads(specifications)
            except json.JSONDecodeError:
                raise BadRequestException("Invalid JSON format for specifications")
        
        dimensions_dict = None
        if dimensions and dimensions.strip():
            try:
                dimensions_dict = json.loads(dimensions)
            except json.JSONDecodeError:
                raise BadRequestException("Invalid JSON format for dimensions")
        
        # Parse tags if provided
        tags_list = None
        if tags and tags.strip():
            tags_list = [tag.strip() for tag in tags.split(",")]
        
        # Create product data
        product_data = ProductCreate(
            name=name,
            description=description,
            category_id=category_id,
            sku=sku,
            price=price,
            discounted_price=discounted_price,
            tax_rate=tax_rate,
            stock=stock,
            requires_prescription=requires_prescription,
            is_active=is_active,
            supplier_id=supplier_id,
            weight=weight,
            reorder_level=reorder_level,
            warranty_period=warranty_period,
            warranty_unit=warranty_unit,
            warranty_description=warranty_description,
            images=",".join(image_paths) if image_paths else None,
            specifications=specifications_dict,
            dimensions=dimensions_dict,
            tags=tags_list
        )
        
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
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    sku: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    discounted_price: Optional[float] = Form(None),
    tax_rate: Optional[float] = Form(None),
    stock: Optional[int] = Form(None),
    requires_prescription: Optional[bool] = Form(None),
    is_active: Optional[bool] = Form(None),
    supplier_id: Optional[int] = Form(None),
    weight: Optional[float] = Form(None),
    reorder_level: Optional[int] = Form(None),
    warranty_period: Optional[int] = Form(None),
    warranty_unit: Optional[str] = Form(None),
    warranty_description: Optional[str] = Form(None),
    specifications: Optional[str] = Form(None),  # JSON string
    dimensions: Optional[str] = Form(None),  # JSON string
    tags: Optional[str] = Form(None),  # Comma-separated string
    images: List[UploadFile] = File([]),
    replace_images: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Updates an existing product with partial data
    
    #### Path Parameters:

    - **product_id**: ID of the product to update
        
    #### Form Fields: (All optional for partial updates)
    
    - **name**: Update product name
    - **description**: Update product description
    - **category_id**: Change product category
    - **sku**: Update SKU (must remain unique)
    - **price**: Update base price
    - **discounted_price**: Update sale price
    - **tax_rate**: Update tax percentage
    - **stock**: Update stock quantity
    - **requires_prescription**: Update prescription requirement
    - **is_active**: Update product status
    - **supplier_id**: Change associated supplier
    - **weight**: Update product weight
    - **reorder_level**: Update reorder threshold
    - **warranty_period**: Update warranty duration
    - **warranty_unit**: Update warranty time unit
    - **warranty_description**: Update warranty details
    - **specifications**: Update technical specifications as JSON string
    - **dimensions**: Update product dimensions as JSON string
    - **tags**: Update product tags as comma-separated string
    - **replace_images**: If true, replaces all existing images; if false, appends new images
        
    #### File Uploads:**
    - **images**: New product image files (optional)
    - **Formats**: JPG, JPEG, PNG, GIF, WebP
    - **Size**: Maximum 5MB per file
        
    #### Image Handling:**
    - **replace_images=false**: New images are added to existing ones
    - **replace_images=true**: All existing images are replaced with new ones
    - **No images uploaded**: Existing images remain unchanged
    """
    try:
        # Get existing product for image handling
        existing_product = await admin_service.get_product_by_id(product_id, db)
        
        # Handle image uploads
        new_image_paths = []
        for image in images:
            if image.filename:
                image_path = await file_service.save_image(image, "products")
                new_image_paths.append(image_path)
        
        # Handle image combination logic
        final_images = None
        if new_image_paths:
            if replace_images:
                # Replace all existing images
                final_images = ",".join(new_image_paths)
            else:
                # Append to existing images
                existing_images = existing_product.images.split(",") if existing_product.images else []
                all_images = existing_images + new_image_paths
                final_images = ",".join(all_images)
        
        # Build update data (only include non-None values)
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if category_id is not None:
            update_data["category_id"] = category_id
        if sku is not None:
            update_data["sku"] = sku
        if price is not None:
            update_data["price"] = price
        if discounted_price is not None:
            update_data["discounted_price"] = discounted_price
        if tax_rate is not None:
            update_data["tax_rate"] = tax_rate
        if stock is not None:
            update_data["stock"] = stock
        if requires_prescription is not None:
            update_data["requires_prescription"] = requires_prescription
        if is_active is not None:
            update_data["is_active"] = is_active
        if supplier_id is not None:
            update_data["supplier_id"] = supplier_id
        if weight is not None:
            update_data["weight"] = weight
        if reorder_level is not None:
            update_data["reorder_level"] = reorder_level
        if warranty_period is not None:
            update_data["warranty_period"] = warranty_period
        if warranty_unit is not None:
            update_data["warranty_unit"] = warranty_unit
        if warranty_description is not None:
            update_data["warranty_description"] = warranty_description
        
        # Handle JSON fields
        if specifications is not None and specifications.strip():
            try:
                update_data["specifications"] = json.loads(specifications)
            except json.JSONDecodeError:
                raise BadRequestException("Invalid JSON format for specifications")
        
        if dimensions is not None and dimensions.strip():
            try:
                update_data["dimensions"] = json.loads(dimensions)
            except json.JSONDecodeError:
                raise BadRequestException("Invalid JSON format for dimensions")
        
        if tags is not None and tags.strip():
            update_data["tags"] = [tag.strip() for tag in tags.split(",")]
        
        # Add images to update data if modified
        if final_images is not None:
            update_data["images"] = final_images
        
        # Create ProductUpdate object
        product_update = ProductUpdate(**update_data)
        
        updated_product = await admin_service.update_product(product_id, product_update, db)
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

