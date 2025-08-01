from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, delete
from typing import List, Optional

from app.models.homepage_section import HomepageSection, homepage_section_products
from app.models.product import Product
from app.schemas.homepage_section import (
    HomepageSectionCreate, 
    HomepageSectionUpdate, 
    HomepageSectionResponse,
    HomepageSectionListResponse,
    SimplifiedHomepageSectionResponse
)
from app.exceptions import NotFoundException


class HomepageSectionService:
    
    async def create_homepage_section(
        self, 
        db: AsyncSession, 
        section_data: HomepageSectionCreate
    ) -> HomepageSectionResponse:
        # Create section
        section = HomepageSection(
            title=section_data.title,
            description=section_data.description,
            display_order=section_data.display_order,
            is_active=section_data.is_active
        )
        
        db.add(section)
        await db.flush()  # Get the ID
        
        # Add products if provided
        if section_data.product_ids:
            await self._add_products_to_section(db, section.id, section_data.product_ids)
        
        await db.commit()
        await db.refresh(section)
        
        # Return with products loaded
        return await self.get_homepage_section_by_id(db, section.id)
    
    async def get_all_homepage_sections(
        self, 
        db: AsyncSession,
        active_only: bool = False,
        include_products: bool = False
    ) -> List[HomepageSectionResponse]:
        query = select(HomepageSection)
        
        if active_only:
            query = query.where(HomepageSection.is_active == True)
        
        if include_products:
            query = query.options(selectinload(HomepageSection.products))
        
        query = query.order_by(HomepageSection.display_order, HomepageSection.created_at)
        
        result = await db.execute(query)
        sections = result.scalars().all()
        
        return [HomepageSectionResponse.model_validate(section) for section in sections]
    
    async def get_simplified_homepage_sections(
        self, 
        db: AsyncSession,
        active_only: bool = False,
        include_products: bool = False
    ) -> List[SimplifiedHomepageSectionResponse]:
        query = select(HomepageSection)
        
        if active_only:
            query = query.where(HomepageSection.is_active == True)
        
        if include_products:
            query = query.options(selectinload(HomepageSection.products))
        
        query = query.order_by(HomepageSection.display_order, HomepageSection.created_at)
        
        result = await db.execute(query)
        sections = result.scalars().all()
        
        return [SimplifiedHomepageSectionResponse.model_validate(section) for section in sections]
    
    async def get_homepage_sections_list(
        self, 
        db: AsyncSession,
        active_only: bool = False
    ) -> List[HomepageSectionListResponse]:
        # Get sections with product count
        query = select(
            HomepageSection,
            func.count(homepage_section_products.c.product_id).label('product_count')
        ).outerjoin(
            homepage_section_products,
            HomepageSection.id == homepage_section_products.c.homepage_section_id
        ).group_by(HomepageSection.id)
        
        if active_only:
            query = query.where(HomepageSection.is_active == True)
        
        query = query.order_by(HomepageSection.display_order, HomepageSection.created_at)
        
        result = await db.execute(query)
        sections_data = result.all()
        
        return [
            HomepageSectionListResponse(
                id=section.id,
                title=section.title,
                description=section.description,
                display_order=section.display_order,
                is_active=section.is_active,
                product_count=product_count,
                created_at=section.created_at
            ) for section, product_count in sections_data
        ]
    
    async def get_homepage_section_by_id(
        self, 
        db: AsyncSession, 
        section_id: int
    ) -> HomepageSectionResponse:
        query = select(HomepageSection).where(
            HomepageSection.id == section_id
        ).options(selectinload(HomepageSection.products))
        
        result = await db.execute(query)
        section = result.scalar_one_or_none()
        
        if not section:
            raise NotFoundException("Homepage section not found")
        
        return HomepageSectionResponse.model_validate(section)
    
    async def update_homepage_section(
        self, 
        db: AsyncSession, 
        section_id: int, 
        section_data: HomepageSectionUpdate
    ) -> HomepageSectionResponse:
        # Get existing section
        query = select(HomepageSection).where(HomepageSection.id == section_id)
        result = await db.execute(query)
        section = result.scalar_one_or_none()
        
        if not section:
            raise NotFoundException("Homepage section not found")
        
        # Update fields
        update_data = section_data.model_dump(exclude_unset=True)
        product_ids = update_data.pop('product_ids', None)
        
        for field, value in update_data.items():
            setattr(section, field, value)
        
        # Update products if provided
        if product_ids is not None:
            # Remove existing products
            await self._remove_all_products_from_section(db, section_id)
            # Add new products
            if product_ids:
                await self._add_products_to_section(db, section_id, product_ids)
        
        await db.commit()
        
        return await self.get_homepage_section_by_id(db, section_id)
    
    async def delete_homepage_section(self, db: AsyncSession, section_id: int) -> bool:
        # Check if section exists
        query = select(HomepageSection).where(HomepageSection.id == section_id)
        result = await db.execute(query)
        section = result.scalar_one_or_none()
        
        if not section:
            raise NotFoundException("Homepage section not found")
        
        await db.delete(section)
        await db.commit()
        return True
    
    async def add_products_to_section(
        self, 
        db: AsyncSession, 
        section_id: int, 
        product_ids: List[int]
    ) -> HomepageSectionResponse:
        # Verify section exists
        await self.get_homepage_section_by_id(db, section_id)
        
        # Add products
        await self._add_products_to_section(db, section_id, product_ids)
        await db.commit()
        
        return await self.get_homepage_section_by_id(db, section_id)
    
    async def remove_products_from_section(
        self, 
        db: AsyncSession, 
        section_id: int, 
        product_ids: List[int]
    ) -> HomepageSectionResponse:
        # Verify section exists
        await self.get_homepage_section_by_id(db, section_id)
        
        # Remove specific products
        for product_id in product_ids:
            delete_stmt = delete(homepage_section_products).where(
                (homepage_section_products.c.homepage_section_id == section_id) &
                (homepage_section_products.c.product_id == product_id)
            )
            await db.execute(delete_stmt)
        
        await db.commit()
        
        return await self.get_homepage_section_by_id(db, section_id)
    
    async def _add_products_to_section(
        self, 
        db: AsyncSession, 
        section_id: int, 
        product_ids: List[int]
    ):
        # Verify products exist
        query = select(Product.id).where(Product.id.in_(product_ids))
        result = await db.execute(query)
        existing_product_ids = [row[0] for row in result.all()]
        
        if len(existing_product_ids) != len(product_ids):
            missing_ids = set(product_ids) - set(existing_product_ids)
            raise NotFoundException(f"Products not found: {missing_ids}")
        
        # Add products to section (avoid duplicates)
        for product_id in product_ids:
            # Check if already exists
            check_query = select(homepage_section_products).where(
                (homepage_section_products.c.homepage_section_id == section_id) &
                (homepage_section_products.c.product_id == product_id)
            )
            existing = await db.execute(check_query)
            
            if not existing.first():
                insert_stmt = homepage_section_products.insert().values(
                    homepage_section_id=section_id,
                    product_id=product_id
                )
                await db.execute(insert_stmt)
    
    async def _remove_all_products_from_section(
        self, 
        db: AsyncSession, 
        section_id: int
    ):
        delete_stmt = delete(homepage_section_products).where(
            homepage_section_products.c.homepage_section_id == section_id
        )
        await db.execute(delete_stmt)


homepage_section_service = HomepageSectionService()
