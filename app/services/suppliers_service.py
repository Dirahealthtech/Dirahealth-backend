from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import exceptions
from ..models.supplier import Supplier
from ..models.user import User
from ..schemas.suppliers import CreateSupplier, UpdateSupplier


class SupplierService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def create_supplier(self, data: CreateSupplier, current_user: User) -> Supplier:
        supplier = data.model_dump()
        supplier_name = supplier["name"]

        # check if the supplier exists
        stmt = select(Supplier).filter_by(name=supplier_name, admin_id=current_user.id)
        result = (await self.db.execute(stmt)).scalar_one_or_none()

        if result:
            raise exceptions.SupplierExistsException()   # supplier already supplies products for current admin user

        new_supplier = Supplier(**supplier, admin_id=current_user.id)
        self.db.add(new_supplier)
        await self.db.commit()
        await self.db.refresh(new_supplier)

        return new_supplier


    async def get_supplier(self, supplier_id: int, current_user: User) -> Supplier:
        result = await self.db.execute(
            select(Supplier).filter_by(id=supplier_id, admin_id=current_user.id)
        )
        supplier = result.scalars().first()
        
        if not supplier:
            raise exceptions.SupplierNotFoundException()

        return supplier


    async def list_suppliers(self, current_user: User) -> list[Supplier]:
        query = select(Supplier).filter_by(admin_id=current_user.id)
        result = await self.db.execute(query)
        return result.scalars().all()


    async def update_supplier(self, supplier_id: int, data: UpdateSupplier, current_user: User) -> Supplier:

        supplier = await self.get_supplier(supplier_id, current_user)

        # exclude fields that have not been explicitly set
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(supplier, field, value)

        await self.db.commit()
        await self.db.refresh(supplier)
        return supplier


    async def delete_supplier(self, supplier_id: int, current_user: User) -> None:

        # check if the supplier provided supplies products for the current admin user
        stmt = select(Supplier).filter_by(id=supplier_id, admin_id=current_user.id)
        result = (await self.db.execute(stmt)).scalars().first()

        if not result:
            raise exceptions.CannotDeleteSupplier()  # current user cannot delete a supplier they didn't add

        supplier = await self.get_supplier(supplier_id, current_user)
        await self.db.delete(supplier)
        await self.db.commit()
