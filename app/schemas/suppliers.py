from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Annotated, Optional


validated_mobile_num = Annotated[str, StringConstraints(min_length=10, max_length=15, pattern=r'^\+?[1-9]\d{1,14}$')]


class BaseSupplierModel(BaseModel):
    name: str
    contact_person: dict
    email: EmailStr
    phone: validated_mobile_num
    tax_id: str
    payment_terms: Optional[str] = None
    lead_time: Optional[int] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class CreateSupplier(BaseSupplierModel):
    pass


class SupplierResponse(BaseSupplierModel):
    id: int
    admin_id: int


class UpdateSupplier(BaseSupplierModel):
    pass
