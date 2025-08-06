from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func
from sqlalchemy.future import select
from typing import List, Optional
import json

from ..core.dependencies import get_db, RoleChecker
from ..enums import UserRole
from ..models import Category, User
from ..schemas.product import (
    ProductCreate, 
    ProductResponse, 
    ProductUpdate,
    ProductListResponse,
    PricingSchema,
    InventorySchema,
    ShippingSchema,
    WarrantySchema,
    MetadataSchema,
    DimensionsSchema
)
from ..schemas import CreateAdminUser
from ..schemas.dashboard import DashboardResponse
from ..services.admin_service import AdminService
from ..services import AuthService
from ..services.file_service import FileService
from ..services.dashboard_service import dashboard_service
from ..exceptions import NotFoundException, BadRequestException, ConflictException
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()

admin_only = Depends(RoleChecker([UserRole.ADMIN]))
admin_service = AdminService()
auth_service = AuthService()
file_service = FileService()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get Dashboard Data - Admin Only**
    
    Retrieve comprehensive dashboard statistics and metrics including:
    
    **Summary Statistics:**
    - Total users, products, categories, orders
    - Total sales revenue and conversion rates
    - Active users and key performance indicators
    
    **Sales Analytics:**
    - Revenue breakdown by time periods (today, week, month, year)
    - Order counts and average order values
    - Top selling products by units and revenue
    
    **Product Management:**
    - Product counts by status (active, inactive, out of stock)
    - Low stock alerts and inventory warnings
    - Category performance and product distribution
    
    **User Analytics:**
    - User registration trends and growth metrics
    - Top buyers by spending and order frequency
    - User engagement and verification statistics
    
    **Order Management:**
    - Order status distribution and fulfillment metrics
    - Latest orders and transaction summaries
    - Revenue tracking and payment analytics
    
    **System Alerts:**
    - Inventory warnings (low stock, out of stock)
    - Pending orders and review management
    - Failed payments and system notifications
    
    **Returns:** Complete dashboard data optimized for admin oversight
    """
    try:
        dashboard_data = await dashboard_service.get_dashboard_data(db)
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )


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

@router.get("/list-categories", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    **List All Categories**
    
    Retrieves a paginated list of all product categories
    
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
    # Basic product info
    name: str = Form(...),
    description: str = Form(...),  # Rich HTML from TinyMCE/WYSIWYG
    category_id: int = Form(...),
    supplier_id: Optional[int] = Form(None),
    
    # Pricing
    price: float = Form(...),
    discounted_price: Optional[float] = Form(0.0),
    tax_rate: Optional[float] = Form(0.0),
    
    # Inventory
    sku: str = Form(...),
    stock: int = Form(...),
    reorder_level: Optional[int] = Form(None),
    requires_prescription: bool = Form(False),
    is_active: bool = Form(True),
    
    # Shipping
    weight: Optional[float] = Form(None),
    dimensions_length: Optional[float] = Form(None),
    dimensions_width: Optional[float] = Form(None),
    dimensions_height: Optional[float] = Form(None),
    dimensions_unit: str = Form("cm"),
    
    # Warranty
    warranty_period: Optional[int] = Form(None),
    warranty_unit: Optional[str] = Form(None),
    warranty_description: Optional[str] = Form(None),
    
    # Metadata
    tags: Optional[str] = Form(None),  # Comma-separated string
    specifications: Optional[str] = Form(None),  # JSON string
    
    # File uploads
    images: List[UploadFile] = File([]),
    
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Creates a new product with structured data format and rich HTML description support.
    
    ### Basic Product Information:
    - **name**: Product name (required)
    - **description**: Rich HTML description from TinyMCE/WYSIWYG editor (required)
    - **category_id**: Product category ID (required)
    - **supplier_id**: Supplier ID (optional, 0 or null for no supplier)
    
    ### Pricing Information:
    - **price**: Base price (required)
    - **discounted_price**: Sale/discounted price (optional, default: 0.0)
    - **tax_rate**: Tax percentage (optional, default: 0.0)
    
    ### Inventory Information:**
    - **sku**: Stock Keeping Unit (required, must be unique)
    - **stock**: Current stock quantity (required)
    - **reorder_level**: Minimum stock for reorder alerts (optional)
    - **requires_prescription**: Prescription requirement (optional, default: false)
    - **is_active**: Product availability status (optional, default: true)
    
    ### Shipping Information:**
    - **weight**: Product weight (optional)
    - **dimensions_length**: Length dimension (optional)
    - **dimensions_width**: Width dimension (optional)
    - **dimensions_height**: Height dimension (optional)
    - **dimensions_unit**: Unit of measurement (optional, default: "cm")
    
    ### Warranty Information:**
    - **warranty_period**: Warranty duration (optional)
    - **warranty_unit**: Warranty time unit (days/months/years) (optional)
    - **warranty_description**: Warranty details (optional)
    
    ### Metadata:**
    - **tags**: Product tags as comma-separated string (optional)
    - **specifications**: Technical specifications as JSON string (optional)
    
    ### File Uploads:**
    - **images**: Multiple product image files (optional, max 10 files, 5MB each)
    
    ### HTML Sanitization:**
    - Description is automatically sanitized to remove dangerous scripts and styles
    - Preserves safe HTML formatting tags for rich content display
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
            if image.filename:
                image_path = await file_service.save_image(image, "products")
                image_paths.append(image_path)
        
        # Parse specifications if provided
        specifications_dict = None
        if specifications and specifications.strip():
            try:
                specifications_dict = json.loads(specifications)
            except json.JSONDecodeError:
                raise BadRequestException("Invalid JSON format for specifications")
        
        # Parse tags if provided
        tags_list = None
        if tags and tags.strip():
            tags_list = [tag.strip() for tag in tags.split(",")]
        
        # Build structured data
        pricing = PricingSchema(
            price=price,
            discounted_price=discounted_price,
            tax_rate=tax_rate
        )
        
        inventory = InventorySchema(
            sku=sku,
            stock=stock,
            reorder_level=reorder_level,
            requires_prescription=requires_prescription,
            is_active=is_active
        )
        
        shipping = None
        if weight or any([dimensions_length, dimensions_width, dimensions_height]):
            dimensions = None
            if any([dimensions_length, dimensions_width, dimensions_height]):
                dimensions = DimensionsSchema(
                    length=dimensions_length,
                    width=dimensions_width,
                    height=dimensions_height,
                    unit=dimensions_unit
                )
            
            shipping = ShippingSchema(
                weight=weight,
                dimensions=dimensions
            )
        
        warranty = None
        if any([warranty_period, warranty_unit, warranty_description]):
            warranty = WarrantySchema(
                period=warranty_period,
                unit=warranty_unit,
                description=warranty_description
            )
        
        metadata = None
        if tags_list or specifications_dict:
            metadata = MetadataSchema(
                tags=tags_list,
                specifications=specifications_dict
            )
        
        # Create product data with structured format
        product_data = ProductCreate(
            name=name,
            description=description,  # Will be sanitized by validator
            category_id=category_id,
            supplier_id=supplier_id,
            pricing=pricing,
            inventory=inventory,
            images=",".join(image_paths) if image_paths else None,
            shipping=shipping,
            warranty=warranty,
            metadata=metadata
        )
        
        new_product = await admin_service.create_product(product_data, db)
        return new_product
        
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to create product: {str(e)}")


@router.get("/list-products", response_model=ProductListResponse)
async def list_products(
    skip: int = 0,
    limit: int = 20,
    name: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    requires_prescription: Optional[bool] = None,
    sort_by: str = "id",
    sort_order: str = "asc",
    db: AsyncSession = Depends(get_db)
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


@router.get("/get-products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db)
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
    # Form fields
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[int] = Form(None),
    supplier_id: Optional[int] = Form(None),
    
    # Pricing fields
    price: Optional[str] = Form(None),
    discounted_price: Optional[str] = Form(None),
    tax_rate: Optional[str] = Form(None),
    
    # Inventory fields
    sku: Optional[str] = Form(None),
    stock: Optional[str] = Form(None),
    reorder_level: Optional[str] = Form(None),
    requires_prescription: Optional[str] = Form(None),
    is_active: Optional[str] = Form(None),
    
    # Shipping fields
    weight: Optional[str] = Form(None),
    dimensions: Optional[str] = Form(None),
    
    # Warranty fields
    warranty_period: Optional[str] = Form(None),
    warranty_unit: Optional[str] = Form(None),
    warranty_description: Optional[str] = Form(None),
    
    # Metadata fields
    specifications: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    
    # File uploads
    images: Optional[List[UploadFile]] = File(None),
    
    # Dependencies
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Update Product**
    
    Updates an existing product with structured data. Supports form-based input with file uploads
    and automatic HTML sanitization for rich text content.
    
    **Path Parameters:**
    - **product_id**: ID of the product to update
        
    **Form Fields:**
    
    **Basic Information:**
    - **name**: Product name
    - **description**: Rich HTML description (sanitized)
    - **category_id**: Category ID
    - **supplier_id**: Supplier ID (0 for no supplier)
    
    **Pricing:**
    - **price**: Base price (JSON string)
    - **discounted_price**: Sale price (JSON string) 
    - **tax_rate**: Tax percentage (JSON string)
    
    **Inventory:**
    - **sku**: Stock keeping unit
    - **stock**: Stock quantity (JSON string)
    - **reorder_level**: Reorder threshold (JSON string)
    - **requires_prescription**: Prescription required (JSON string)
    - **is_active**: Product status (JSON string)
    
    **Shipping:**
    - **weight**: Product weight (JSON string)
    - **dimensions**: Dimensions object (JSON string)
    
    **Warranty:**
    - **warranty_period**: Warranty duration (JSON string)
    - **warranty_unit**: Warranty time unit (JSON string)
    - **warranty_description**: Warranty details (JSON string)
    
    **Metadata:**
    - **specifications**: Technical specs (JSON string)
    - **tags**: Product tags (JSON string)
    
    **Files:**
    - **images**: Product images (file uploads)
    """
    try:
        # Process form data into structured format
        form_data = {}
        
        # Basic fields
        if name is not None:
            form_data["name"] = name
        if description is not None:
            form_data["description"] = description
        if category_id is not None:
            form_data["category_id"] = category_id
        if supplier_id is not None:
            form_data["supplier_id"] = supplier_id
        
        # Handle images
        if images:
            # Upload new images
            uploaded_paths = []
            for image in images:
                if image.filename:
                    path = await file_service.save_image(image, "products")
                    uploaded_paths.append(path)
            if uploaded_paths:
                form_data["images"] = uploaded_paths
        
        # Build structured data
        pricing_data = {}
        if price is not None and price.strip():
            pricing_data["price"] = float(price)
        if discounted_price is not None and discounted_price.strip():
            pricing_data["discounted_price"] = float(discounted_price)
        if tax_rate is not None and tax_rate.strip():
            pricing_data["tax_rate"] = float(tax_rate)
        
        inventory_data = {}
        if sku is not None:
            inventory_data["sku"] = sku
        if stock is not None and stock.strip():
            inventory_data["stock"] = int(stock)
        if reorder_level is not None and reorder_level.strip():
            inventory_data["reorder_level"] = int(reorder_level)
        if requires_prescription is not None and requires_prescription.strip():
            inventory_data["requires_prescription"] = requires_prescription.lower() == "true"
        if is_active is not None and is_active.strip():
            inventory_data["is_active"] = is_active.lower() == "true"
        
        shipping_data = {}
        if weight is not None and weight.strip():
            shipping_data["weight"] = float(weight)
        if dimensions is not None and dimensions.strip():
            dimensions_json = json.loads(dimensions)
            shipping_data["dimensions"] = dimensions_json
        
        warranty_data = {}
        if warranty_period is not None and warranty_period.strip():
            warranty_data["period"] = int(warranty_period)
        if warranty_unit is not None:
            warranty_data["unit"] = warranty_unit
        if warranty_description is not None:
            warranty_data["description"] = warranty_description
        
        metadata_data = {}
        if specifications is not None and specifications.strip():
            metadata_data["specifications"] = json.loads(specifications)
        if tags is not None and tags.strip():
            metadata_data["tags"] = json.loads(tags)
        
        # Add nested objects only if they have data
        if pricing_data:
            form_data["pricing"] = pricing_data
        if inventory_data:
            form_data["inventory"] = inventory_data
        if shipping_data:
            form_data["shipping"] = shipping_data
        if warranty_data:
            form_data["warranty"] = warranty_data
        if metadata_data:
            form_data["metadata"] = metadata_data
        
        # Create ProductUpdate instance
        product_data = ProductUpdate(**form_data)
        
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

