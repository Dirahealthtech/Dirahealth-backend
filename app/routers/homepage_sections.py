from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_db, RoleChecker
from app.enums import UserRole
from app.schemas.homepage_section import (
    HomepageSectionCreate,
    HomepageSectionUpdate,
    HomepageSectionResponse,
    HomepageSectionListResponse
)
from app.services.homepage_section_service import homepage_section_service
from app.exceptions import NotFoundException


router = APIRouter(prefix="/homepage-sections", tags=["Homepage Sections"])

admin_only = Depends(RoleChecker([UserRole.ADMIN]))


# Public endpoints for displaying homepage sections
@router.get("/", response_model=List[HomepageSectionResponse])
async def get_homepage_sections(
    active_only: bool = Query(True, description="Only return active sections"),
    include_products: bool = Query(True, description="Include products in response"),
    db: AsyncSession = Depends(get_db)
):
    """
    **Get All Homepage Sections**
    
    Retrieves all homepage sections for public display with optional filtering and product inclusion.
    
    **Query Parameters:**
    
    - **active_only**: Only return active sections (default: true)
    - **include_products**: Include associated products in response (default: true)
    
    **Returns:**
    
    - Array of homepage sections with their details and associated products (if requested)
    - Sections are ordered by display_order and creation date
    """
    try:
        sections = await homepage_section_service.get_all_homepage_sections(
            db=db, 
            active_only=active_only,
            include_products=include_products
        )
        return sections
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching homepage sections: {str(e)}"
        )


@router.get("/{section_id}", response_model=HomepageSectionResponse)
async def get_homepage_section(
    section_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    **Get Specific Homepage Section**
    
    Retrieves a specific homepage section by its ID with all associated products.
    
    **Path Parameters:**
    
    - **section_id**: Unique identifier of the homepage section
    
    **Returns:**
    
    - Complete homepage section details including associated products
    - Section title, description, display order, and product list
    """
    try:
        section = await homepage_section_service.get_homepage_section_by_id(db, section_id)
        return section
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching homepage section: {str(e)}"
        )


# Admin endpoints for managing homepage sections
@router.post("/admin", response_model=HomepageSectionResponse, status_code=status.HTTP_201_CREATED)
async def create_homepage_section(
    section_data: HomepageSectionCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Create New Homepage Section**
    
    Creates a new homepage section for promotional content management.
    Only accessible by admin users.
    
    **Request Body:**
    
    - **title**: Section title (required) - e.g., "Flash Sales", "Black Friday Offers"
    - **description**: Section description (optional) - detailed explanation of the section
    - **display_order**: Display order on homepage (optional, default: 0)
    - **is_active**: Section active status (optional, default: true)
    - **product_ids**: Array of product IDs to associate with section (optional)
    
    **Returns:**
    
    - Created homepage section with complete details and associated products
    
    **Use Cases:**
    
    - Create promotional sections like "Flash Sales", "What's New", "Black Friday Offers"
    - Organize products into themed collections for homepage display
    - Manage seasonal or event-based product groupings
    """
    try:
        section = await homepage_section_service.create_homepage_section(db, section_data)
        return section
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating homepage section: {str(e)}"
        )


@router.put("/admin/{section_id}", response_model=HomepageSectionResponse)
async def update_homepage_section(
    section_id: int,
    section_data: HomepageSectionUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Update Homepage Section**
    
    Updates an existing homepage section with new information and/or product associations.
    Supports partial updates. Only accessible by admin users.
    
    **Path Parameters:**
    
    - **section_id**: ID of the homepage section to update
    
    **Request Body:** (All fields optional for partial updates)
    
    - **title**: Update section title
    - **description**: Update section description  
    - **display_order**: Update display order on homepage
    - **is_active**: Update section active status
    - **product_ids**: Replace all associated products with new list
    
    **Returns:**
    
    - Updated homepage section with complete details and current product associations
    
    **Notes:**
    
    - If product_ids is provided, it replaces ALL existing product associations
    - To add/remove specific products, use the dedicated product management endpoints
    """
    try:
        section = await homepage_section_service.update_homepage_section(db, section_id, section_data)
        return section
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating homepage section: {str(e)}"
        )


@router.delete("/admin/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_homepage_section(
    section_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Delete Homepage Section**
    
    Permanently deletes a homepage section and all its product associations.
    Only accessible by admin users.
    
    **Path Parameters:**
    
    - **section_id**: ID of the homepage section to delete
    
    **Returns:**
    
    - No content (204 status code) on successful deletion
    
    **Notes:**
    
    - This action is permanent and cannot be undone
    - All product associations are removed, but products themselves remain unaffected
    - Consider deactivating sections instead of deleting for data preservation
    """
    try:
        await homepage_section_service.delete_homepage_section(db, section_id)
        return
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting homepage section: {str(e)}"
        )


@router.post("/admin/{section_id}/products", response_model=HomepageSectionResponse)
async def add_products_to_section(
    section_id: int,
    product_ids: List[int],
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Add Products to Homepage Section**
    
    Associates additional products with an existing homepage section.
    Only accessible by admin users.
    
    **Path Parameters:**
    
    - **section_id**: ID of the homepage section to update
    
    **Request Body:**
    
    - **product_ids**: Array of product IDs to add to the section
    
    **Returns:**
    
    - Updated homepage section with all associated products including newly added ones
    
    **Notes:**
    
    - Products are validated to exist before association
    - Duplicate associations are automatically prevented
    - Existing product associations remain unchanged
    - Use this to incrementally build product collections
    """
    try:
        section = await homepage_section_service.add_products_to_section(db, section_id, product_ids)
        return section
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding products to section: {str(e)}"
        )


@router.delete("/admin/{section_id}/products", response_model=HomepageSectionResponse)
async def remove_products_from_section(
    section_id: int,
    product_ids: List[int],
    db: AsyncSession = Depends(get_db),
    _: dict = admin_only
):
    """
    **Remove Products from Homepage Section**
    
    Removes specific product associations from a homepage section.
    Only accessible by admin users.
    
    **Path Parameters:**
    
    - **section_id**: ID of the homepage section to update
    
    **Request Body:**
    
    - **product_ids**: Array of product IDs to remove from the section
    
    **Returns:**
    
    - Updated homepage section with remaining associated products
    
    **Notes:**
    
    - Only removes the association between products and section
    - Products themselves remain in the system unchanged
    - Non-existent associations are silently ignored
    - Use this to curate and maintain section content
    """
    try:
        section = await homepage_section_service.remove_products_from_section(db, section_id, product_ids)
        return section
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing products from section: {str(e)}"
        )
