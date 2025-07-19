from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import and_, desc, func
from sqlalchemy.future import select
from sqlalchemy import update
from typing import List, Optional
from uuid import uuid4
import os
import shutil

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
    Initial setup only: Create the first admin user
    This endpoint should be secured or disabled in production
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
    Create a new user with specified role
    NB -> An admin only endpoint
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
    Update a user's role - Admin only
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
@router.post("/categories/{category_id}/image", response_model=CategoryResponse)
async def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Upload an image for a category - Admin only
    """
    try:
        # Validate file is an image
        if not file.content_type.startswith("image/"):
            raise BadRequestException("File provided is not an image")
        
        # Check if category exists
        category = await admin_service.get_category_by_id(category_id, db)
        
        # Create directory if it doesn't exist
        upload_dir = "uploads/categories"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        new_filename = f"category-{category_id}-{uuid4().hex}.{file_extension}"
        file_path = f"{upload_dir}/{new_filename}"
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise BadRequestException(f"Failed to save file: {str(e)}")
        
        # Update category image_url
        image_url = f"/uploads/categories/{new_filename}"
        
        # Update the category directly using SQLAlchemy
        stmt = (
            update(Category)
            .where(Category.id == category_id)
            .values(image_url=image_url)
            .execution_options(synchronize_session="fetch")
        )
        
        await db.execute(stmt)
        await db.commit()
        
        # Get updated category
        updated_category = await admin_service.get_category_by_id(category_id, db)
        
        return updated_category
    
    except NotFoundException as e:
        raise e
    except BadRequestException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to upload category image: {str(e)}")

@router.post("/categories", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    Create a new category - Admin only
    """
    try:
        # Create a category
        new_category = Category(
            name=category_data.name,
            slug=category_data.name.lower().replace(" ", "-"),
            description=category_data.description,
            parent_id=category_data.parent_id,
            image_url=category_data.image_url,
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
    List all categories
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
    Update an existing category - **admin only**
    - **category_id(int)**: the id of the category to update
    - **name(str)**: Update name of the category
    - **description(str)**: Update the category description
    - **parent_id(int)** : Update the parent category for this category
    - **image_url(str)**: Update the image url for the category
    - **is_active(bool)**: Update the status of the category i.e True or False

    **NB:** Only the category id is mandatory
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
    Delete a category by its id
    Args:
        - **category_id(int):** Mandatory Category ID for the category to delete
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
    Create a new product - Admin only
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
    List all products with filtering and sorting - Admin only
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
    Get a specific product by ID - Admin only
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
    Update a specific product - Admin only
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


# Upload multiple product images endpoint
@router.post("/products/{product_id}/images", response_model=ProductResponse)
async def upload_product_images(
    product_id: int,
    files: List[UploadFile] = File(...),
    replace_existing: bool = Form(False),
    main_image_index: int = Form(0),
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only  # Admin check
):
    """
    Upload multiple images for a product - Admin only
    
    Args:
        - **product_id**: ID of the product to update
        - **files**: List of image files to upload
        - **replace_existing**: Whether to replace existing images or append to them (default: False)
        - **main_image_index**: Index of the image that should be marked as main (default: 0)
    """
    try:
        if not files:
            raise BadRequestException("No files provided")
        
        if main_image_index >= len(files) or main_image_index < 0:
            raise BadRequestException(f"Invalid main_image_index. Must be between 0 and {len(files) - 1}")
        
        # Validate all files are images
        for file in files:
            if not file.content_type.startswith("image/"):
                raise BadRequestException(f"File '{file.filename}' is not an image")
        
        # Create directory if it doesn't exist
        upload_dir = "uploads/products"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save all files and collect URLs
        image_urls = []
        for i, file in enumerate(files):
            # Generate unique filename
            file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
            new_filename = f"product-{product_id}-{uuid4().hex}.{file_extension}"
            file_path = f"{upload_dir}/{new_filename}"
            
            # Save file
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
            except Exception as e:
                # Clean up any already saved files
                for saved_url in image_urls:
                    try:
                        saved_path = saved_url.replace("/uploads/products/", f"{upload_dir}/")
                        if os.path.exists(saved_path):
                            os.remove(saved_path)
                    except:
                        pass
                raise BadRequestException(f"Failed to save file '{file.filename}': {str(e)}")
            
            image_url = f"/uploads/products/{new_filename}"
            image_urls.append(image_url)
        
        # Update product with all images
        updated_product = await admin_service.update_product_images(
            product_id, 
            image_urls, 
            replace_existing=replace_existing,
            main_image_index=main_image_index,
            db=db
        )
        
        return updated_product
    
    except NotFoundException as e:
        raise e
    except BadRequestException as e:
        raise e
    except Exception as e:
        raise BadRequestException(f"Failed to upload images: {str(e)}")


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

