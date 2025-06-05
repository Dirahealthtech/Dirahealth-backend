from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_db, get_current_admin, RoleChecker
from ..enums import UserRole
from ..models import User
from ..schemas.suppliers import CreateSupplier, SupplierResponse, UpdateSupplier
from ..services.suppliers_service import SupplierService
from typing import List


router = APIRouter()
admins_only = Depends(RoleChecker([UserRole.ADMIN]))


async def get_supplier_service(db: AsyncSession = Depends(get_db)) -> SupplierService:
    return SupplierService(db)


@router.get('/', dependencies=[admins_only], response_model=List[SupplierResponse])
async def get_all_suppliers(
    service: SupplierService = Depends(get_supplier_service),
    current_user: User = Depends(get_current_admin),
):
    return await service.list_suppliers(current_user)


@router.get('/{id}/supplier', dependencies=[admins_only], response_model=SupplierResponse)
async def get_product_supplier_by_id(
    id: int = Path(..., description='ID of the supplier'),
    service: SupplierService = Depends(get_supplier_service),
    current_user: User = Depends(get_current_admin),
):
    return await service.get_supplier(id, current_user)


@router.post('/add-supplier', dependencies=[admins_only], response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
async def add_product_supplier(
    supplier: CreateSupplier,
    service: SupplierService = Depends(get_supplier_service),
    current_user: User = Depends(get_current_admin),
):
    return await service.create_supplier(supplier,  current_user)


@router.put('/{id}/update-supplier', dependencies=[admins_only], response_model=SupplierResponse)
async def update_product_supplier(
    data: UpdateSupplier,
    id: int = Path(..., description="ID of the supplier"),
    service: SupplierService = Depends(get_supplier_service),
    current_user: User = Depends(get_current_admin),
):

    return await service.update_supplier(id, data, current_user)


@router.delete('/{id}/delete-supplier', status_code=status.HTTP_204_NO_CONTENT)
async def delete_product_supplier(
    id: int = Path(..., description="ID of the supplier"),
    service: SupplierService = Depends(get_supplier_service),
    current_user: User = Depends(get_current_admin),
):
    return await service.delete_supplier(id, current_user)
