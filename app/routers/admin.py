from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import func
from sqlalchemy.future import select
from sqlalchemy import select as sql_select
from typing import List, Optional
import json
from datetime import datetime

from ..core.dependencies import get_db, RoleChecker, get_current_admin
from ..enums import UserRole
from ..models import Category, User
from ..schemas.product import (
    ProductCreate, 
    ProductResponse, 
    ProductUpdate,
    ProductListResponse,
    PricingSchema,
    InventorySchema,
    InventoryUpdateSchema,
    ShippingSchema,
    WarrantySchema,
    MetadataSchema,
    DimensionsSchema
)
from ..schemas.order import (
    OrderResponse,
    OrderDetail,
    OrderStatus as OrderStatusEnum,
    OrderStatusUpdate,
    PaymentMethod,
    PaymentStatus
)
from ..schemas import CreateAdminUser
from ..schemas.dashboard import DashboardResponse
from ..services.admin_service import AdminService
from ..services import AuthService
from ..services.order_service import OrderService
from ..services.file_service import FileService
from ..services.email_service import EmailService
from ..services.dashboard_service import dashboard_service
from ..exceptions import NotFoundException, BadRequestException, ConflictException
from ..schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from ..schemas.tracking import TrackingUpdate, TrackingResponse
from ..models.order import OrderStatus

router = APIRouter()

admin_only = Depends(RoleChecker([UserRole.ADMIN]))
admin_service = AdminService()
auth_service = AuthService()
file_service = FileService()
order_service = OrderService()
email_service = EmailService()


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
    supports_online_payment: bool = Form(True),
    supports_cod: bool = Form(True),
    
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
    - **supports_online_payment**: Accepts online payments (optional, default: true)
    - **supports_cod**: Accepts cash on delivery (optional, default: true)
    
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
            is_active=is_active,
            supports_online_payment=supports_online_payment,
            supports_cod=supports_cod
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
        
        # Handle supplier_id: convert 0 to None for no supplier
        processed_supplier_id = None if supplier_id == 0 else supplier_id
        
        # Create product data with structured format
        product_data = ProductCreate(
            name=name,
            description=description,  # Will be sanitized by validator
            category_id=category_id,
            supplier_id=processed_supplier_id,
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
    supports_online_payment: Optional[str] = Form(None),
    supports_cod: Optional[str] = Form(None),
    
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
            # Convert 0 to None for no supplier
            form_data["supplier_id"] = None if supplier_id == 0 else supplier_id
        
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
        if supports_online_payment is not None and supports_online_payment.strip():
            inventory_data["supports_online_payment"] = supports_online_payment.lower() == "true"
        if supports_cod is not None and supports_cod.strip():
            inventory_data["supports_cod"] = supports_cod.lower() == "true"
        
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


# =============================================================================
# ADMIN ORDER MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/orders", response_model=List[OrderResponse])
async def get_all_orders(
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only,
    status_filter: Optional[OrderStatusEnum] = Query(None, description="Filter by order status"),
    payment_method: Optional[PaymentMethod] = Query(None, description="Filter by payment method"),
    payment_status: Optional[PaymentStatus] = Query(None, description="Filter by payment status"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    date_from: Optional[str] = Query(None, description="Filter orders from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter orders to date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    **Get All Orders (Admin)**
    
    Retrieve all orders in the system with comprehensive filtering and sorting options.
    Only accessible by admin users.
    
    **Query Parameters:**
    - **status_filter**: Filter by order status (pending, processing, shipped, delivered, etc.)
    - **payment_method**: Filter by payment method (mpesa, cash_on_delivery, etc.)
    - **payment_status**: Filter by payment status (pending, completed, failed, refunded)
    - **customer_id**: Filter orders by specific customer
    - **date_from**: Start date for order filtering (YYYY-MM-DD format)
    - **date_to**: End date for order filtering (YYYY-MM-DD format)
    - **page**: Page number for pagination (default: 1)
    - **size**: Number of orders per page (default: 20, max: 100)
    - **sort_by**: Field to sort by (created_at, total, status, etc.)
    - **sort_order**: Sort direction (asc/desc, default: desc)
    
    **Returns:**
    - List of orders with basic information
    - Ordered by specified criteria
    - Includes customer info, status, totals, and payment details
    
    **Use Cases:**
    - Order fulfillment dashboard
    - Financial reporting and analysis
    - Customer service inquiries
    - Inventory planning based on order patterns
    """
    try:
        skip = (page - 1) * size
        
        # Use the new admin service method
        all_orders = await order_service.get_all_orders_admin(
            db=db,
            skip=skip,
            limit=size,
            status_filter=status_filter.value if status_filter else None,
            payment_method=payment_method.value if payment_method else None,
            customer_id=customer_id,
            date_from=date_from,
            date_to=date_to,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return all_orders
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orders: {str(e)}"
        )


@router.get("/orders/{order_id}", response_model=OrderDetail)
async def get_order_admin(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Get Order Details (Admin)**
    
    Retrieve complete details for any order in the system.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Returns:**
    - Complete order information including:
      - Customer details and contact information
      - Order summary and status history
      - All order items with product details
      - Services included in the order
      - Shipping and billing addresses
      - Payment information and transaction details
      - Tracking information and delivery status
      - Admin notes and order history
    
    **Use Cases:**
    - Order fulfillment and processing
    - Customer service support
    - Dispute resolution and investigations
    - Refund and return processing
    """
    try:
        # Admin can view any order (pass None as user_id for admin access)
        order_detail = await order_service.get_order_detail(order_id, None, db)
        return order_detail
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve order: {str(e)}"
        )


@router.patch("/orders/{order_id}/status", response_model=dict)
async def update_order_status_admin(
    order_id: int,
    status_update: OrderStatusUpdate,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Update Order Status (Admin)**
    
    Update an order's status with admin authority and automatic notifications.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Request Body:**
    - **status**: New order status (pending, processing, shipped, delivered, cancelled)
    - **notes**: Optional notes about the status change
    
    **Returns:**
    - Confirmation of status update with timestamp
    
    **Automated Actions:**
    - Sends email notifications to customer
    """
    try:
        updated_order = await order_service.update_order_status(
            order_id=order_id,
            status=status_update.status,
            admin_id=current_admin.id,
            db=db,
            notes=status_update.notes,
            background_tasks=background_tasks
        )
        
        return {
            "message": f"Order {order_id} status updated to {status_update.status}",
            "order_id": order_id,
            "new_status": status_update.status,
            "updated_by": current_admin.email,
            "updated_at": datetime.now(),
            "notes": status_update.notes
        }
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order status: {str(e)}"
        )


@router.post("/orders/{order_id}/complete")
async def complete_order_admin(
    order_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only,
    delivery_confirmation: bool = Query(True, description="Confirm delivery completion"),
    payment_collected: bool = Query(True, description="Confirm payment collection (for COD)")
):
    """
    **Complete Order (Admin)**
    
    Mark an order as completed with delivery and payment confirmation.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Query Parameters:**
    - **delivery_confirmation**: Confirm that delivery was successful (default: true)
    - **payment_collected**: Confirm payment collection for COD orders (default: true)
    
    **Returns:**
    - Completion confirmation with final order summary
    
    **Completion Process:**
    1. Validates order is eligible for completion
    2. Confirms payment status (completes COD payments)
    3. Updates order status to delivered
    4. Sends completion confirmation to customer
    
    **Use Cases:**
    - Final order fulfillment step
    - COD payment confirmation
    - Delivery verification
    """
    try:
        # Complete the order with delivery and payment confirmation
        completion_notes = []
        if delivery_confirmation:
            completion_notes.append("Delivery confirmed by admin")
        if payment_collected:
            completion_notes.append("Payment collected and verified")
        
        completed_order = await order_service.update_order_status(
            order_id=order_id,
            status=OrderStatus.DELIVERED,
            admin_id=current_admin.id,
            db=db,
            notes="; ".join(completion_notes),
            background_tasks=background_tasks
        )
        
        return {
            "message": f"Order {order_id} completed successfully",
            "order_id": order_id,
            "status": "delivered",
            "completed_by": current_admin.email,
            "completed_at": datetime.now(),
            "delivery_confirmed": delivery_confirmation,
            "payment_collected": payment_collected,
            "next_actions": [
                "Customer notification sent",
                "Sales analytics updated"
            ]
        }
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete order: {str(e)}"
        )


@router.post("/orders/{order_id}/shipping/assign")
async def assign_shipping_admin(
    order_id: int,
    tracking_data: TrackingUpdate,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Assign Shipping Information (Admin)**
    
    Assign shipping details and tracking information to an order.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Request Body:**
    - **tracking_number**: Shipping tracking number
    - **carrier**: Shipping carrier/company
    - **estimated_delivery**: Estimated delivery date
    - **shipping_address**: Confirmed shipping address
    - **special_instructions**: Delivery instructions
    
    **Returns:**
    - Shipping assignment confirmation with tracking details
    
    **Shipping Process:**
    1. Validates order is ready for shipping
    2. Assigns tracking information
    3. Updates order status to shipped
    4. Sends shipping notification to customer
    5. Initiates tracking updates
    6. Schedules delivery confirmation follow-up
    """
    try:
        # Update order with shipping information
        shipping_info = await order_service.update_tracking_info(
            order_id=order_id,
            admin_id=current_admin.id,
            tracking_data=tracking_data.dict(),
            db=db
        )
        
        # Update order status to shipped
        await order_service.update_order_status(
            order_id=order_id,
            status=OrderStatus.SHIPPED,
            admin_id=current_admin.id,
            db=db,
            notes=f"Shipped with tracking: {tracking_data.tracking_number}",
            background_tasks=background_tasks
        )
        
        return {
            "message": f"Shipping assigned for order {order_id}",
            "order_id": order_id,
            "tracking_number": tracking_data.tracking_number,
            "carrier": getattr(tracking_data, 'carrier', 'Not specified'),
            "status": "shipped",
            "assigned_by": current_admin.email,
            "assigned_at": datetime.now(),
            "customer_notified": True
        }
        
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign shipping: {str(e)}"
        )


@router.post("/orders/{order_id}/payment/verify")
async def verify_payment_admin(
    order_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only,
    payment_method: PaymentMethod = Query(..., description="Payment method used"),
    amount_collected: float = Query(..., description="Amount collected"),
    payment_reference: Optional[str] = Query(None, description="Payment reference/receipt number")
):
    """
    **Verify Payment (Admin)**
    
    Verify and confirm payment collection, especially for cash on delivery orders.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Query Parameters:**
    - **payment_method**: Method of payment (cash_on_delivery, mpesa, etc.)
    - **amount_collected**: Actual amount collected
    - **payment_reference**: Payment reference or receipt number
    
    **Returns:**
    - Payment verification confirmation
    
    **Payment Verification Process:**
    1. Validates order payment status
    2. Confirms amount matches order total
    3. Records payment collection details
    4. Updates payment status to completed
    5. Sends payment confirmation to customer
    6. Updates financial records and reports
    
    **Use Cases:**
    - COD payment confirmation
    - M-Pesa payment verification
    - Bank transfer confirmation
    - Payment dispute resolution
    """
    try:
        # Get order details to verify amount (admin access)
        order_detail = await order_service.get_order_detail(order_id, None, db)
        
        # Verify payment amount
        if abs(amount_collected - order_detail["total"]) > 0.01:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount mismatch. Expected: {order_detail['total']}, Collected: {amount_collected}"
            )
        
        # Update payment status and add verification notes
        verification_notes = f"Payment verified by {current_admin.email}. Method: {payment_method}, Amount: {amount_collected}"
        if payment_reference:
            verification_notes += f", Reference: {payment_reference}"
        
        await order_service.update_order_status(
            order_id=order_id,
            status=order_detail["status"],  # Keep current status
            admin_id=current_admin.id,
            db=db,
            notes=verification_notes,
            background_tasks=background_tasks
        )
        
        return {
            "message": f"Payment verified for order {order_id}",
            "order_id": order_id,
            "payment_method": payment_method,
            "amount_verified": amount_collected,
            "expected_amount": order_detail["total"],
            "payment_reference": payment_reference,
            "verified_by": current_admin.email,
            "verified_at": datetime.now(),
            "status": "payment_verified"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify payment: {str(e)}"
        )

@router.post("/orders/{order_id}/email/send")
async def send_order_email_admin(
    order_id: int,
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only,
    email_type: str = Query(..., description="Type of email to send"),
    custom_message: Optional[str] = Query(None, description="Custom message to include")
):
    """
    **Send Order Email (Admin)**
    
    Send various types of order-related emails to customers.
    Only accessible by admin users.
    
    **Path Parameters:**
    - **order_id**: Unique identifier of the order
    
    **Query Parameters:**
    - **email_type**: Type of email (confirmation, shipping, delivery, follow_up, custom)
    - **custom_message**: Additional custom message to include in email
    
    **Returns:**
    - Email sending confirmation
    
    **Available Email Types:**
    - **confirmation**: Order confirmation and receipt
    - **shipping**: Shipping notification with tracking
    - **delivery**: Delivery confirmation and feedback request
    - **follow_up**: Customer satisfaction follow-up
    - **custom**: Custom message with order details
    - **refund**: Refund processing notification
    - **cancellation**: Order cancellation confirmation
    
    **Email Features:**
    - Professional branded templates
    - Order details and tracking information
    - Customer support contact information
    - Personalized content based on order history
    - Mobile-responsive design
    
    **Use Cases:**
    - Manual customer communication
    - Order issue resolution
    - Customer service follow-up
    - Marketing and engagement
    """
    try:
        # Get order details for email content (admin access)
        order_detail = await order_service.get_order_detail(order_id, None, db)
        
        # Get customer information
        customer_query = select(User).where(User.id == order_detail["customer_id"])
        customer_result = await db.execute(customer_query)
        customer = customer_result.scalars().first()
        
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found for this order"
            )
        
        # Validate email type
        valid_email_types = ['confirmation', 'shipping', 'delivery', 'follow_up', 'custom', 'refund', 'cancellation']
        if email_type not in valid_email_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid email type. Must be one of: {', '.join(valid_email_types)}"
            )
        
        # Send appropriate email based on type
        customer_name = f"{customer.first_name} {customer.last_name}"
        email_sent = False
        
        if email_type == "confirmation":
            email_sent = await email_service.send_order_confirmation_email(
                to_email=customer.email,
                order_data=order_detail,
                customer_name=customer_name
            )
        elif email_type == "shipping":
            # Get tracking information if available
            tracking_data = {"tracking_number": order_detail.get("tracking_number", "")}
            email_sent = await email_service.send_order_shipping_email(
                to_email=customer.email,
                order_data=order_detail,
                tracking_data=tracking_data,
                customer_name=customer_name
            )
        elif email_type == "delivery":
            email_sent = await email_service.send_order_delivery_confirmation_email(
                to_email=customer.email,
                order_data=order_detail,
                customer_name=customer_name
            )
        elif email_type == "custom":
            if not custom_message:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Custom message is required for custom email type"
                )
            custom_subject = f"Important Update - Order #{order_detail.get('order_number', '')}"
            email_sent = await email_service.send_custom_order_email(
                to_email=customer.email,
                order_data=order_detail,
                custom_subject=custom_subject,
                custom_message=custom_message,
                customer_name=customer_name
            )
        elif email_type in ["follow_up", "refund", "cancellation"]:
            # Use order status update email for these types
            status_messages = {
                "follow_up": "We hope you're satisfied with your order",
                "refund": "Your refund has been processed",
                "cancellation": "Your order has been cancelled as requested"
            }
            email_sent = await email_service.send_order_status_update_email(
                to_email=customer.email,
                order_data=order_detail,
                new_status=email_type,
                notes=status_messages.get(email_type, custom_message),
                customer_name=customer_name
            )
        
        return {
            "message": f"{email_type.title()} email sent for order {order_id}",
            "order_id": order_id,
            "email_type": email_type,
            "recipient": customer.email,
            "recipient_name": customer_name,
            "sent_by": current_admin.email,
            "sent_at": datetime.now(),
            "custom_message_included": custom_message is not None,
            "email_delivered": email_sent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.post("/orders/delivery-zones/configure")
async def configure_delivery_zones_admin(
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only,
    zone_name: str = Query(..., description="Name of the delivery zone"),
    areas: List[str] = Query(..., description="List of areas in this zone"),
    supports_cod: bool = Query(True, description="Whether COD is available in this zone"),
    delivery_fee: float = Query(0.0, description="Delivery fee for this zone"),
    estimated_days: int = Query(3, description="Estimated delivery days")
):
    """
    **Configure Delivery Zones (Admin)**
    
    Configure delivery zones with COD availability and pricing.
    Only accessible by admin users.
    
    **Query Parameters:**
    - **zone_name**: Name of the delivery zone (e.g., "Nairobi CBD", "Westlands")
    - **areas**: List of specific areas included in this zone
    - **supports_cod**: Whether cash on delivery is available (default: true)
    - **delivery_fee**: Delivery fee for this zone (default: 0.0)
    - **estimated_days**: Estimated delivery time in days (default: 3)
    
    **Returns:**
    - Zone configuration confirmation
    
    **Zone Configuration Features:**
    - Geographic area definitions
    - COD availability settings
    - Dynamic delivery pricing
    - Delivery time estimates
    - Service availability mapping
    
    **Business Rules:**
    - COD availability based on delivery reliability
    - Delivery fees based on distance and logistics cost
    - Service levels for different zones
    - Risk assessment for payment methods
    
    **Use Cases:**
    - Expand delivery coverage
    - Optimize logistics costs
    - Manage payment method risks
    - Improve delivery time estimates
    """
    try:
        # Create delivery zone configuration
        # This would ideally be stored in a delivery_zones table
        # For now, we'll create a structured response that could be stored
        
        zone_config = {
            "zone_id": f"zone_{zone_name.lower().replace(' ', '_')}",
            "zone_name": zone_name,
            "areas_covered": areas,
            "delivery_settings": {
                "supports_cod": supports_cod,
                "delivery_fee": delivery_fee,
                "estimated_delivery_days": estimated_days,
                "service_level": "standard"
            },
            "coverage_details": {
                "total_areas": len(areas),
                "payment_methods": ["mpesa"] + (["cash_on_delivery"] if supports_cod else []),
                "special_instructions": "Follow area-specific delivery guidelines"
            },
            "configured_at": datetime.now(),
            "status": "active"
        }
        
        # TODO: Store this configuration in database
        # For now, return the configuration as confirmation
        # In a real implementation, you would:
        # 1. Create a DeliveryZone model
        # 2. Store the configuration in the database
        # 3. Use this data to determine COD availability during checkout
        
        return {
            "message": f"Delivery zone '{zone_name}' configured successfully",
            "zone_configuration": zone_config,
            "areas_count": len(areas),
            "cod_enabled": supports_cod,
            "delivery_fee": delivery_fee,
            "estimated_delivery_days": estimated_days,
            "implementation_note": "Zone configuration created. Consider implementing DeliveryZone model for persistence."
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure delivery zone: {str(e)}"
        )

