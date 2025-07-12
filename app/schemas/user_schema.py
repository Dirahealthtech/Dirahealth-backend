from pydantic import BaseModel, EmailStr, Field, StringConstraints
from typing import Annotated, Optional


validated_mobile_num = Annotated[str, StringConstraints(min_length=10, max_length=15, pattern=r'^\+?[1-9]\d{1,14}$')]

class BaseUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: validated_mobile_num
    hashed_password: str = Field(min_length=8)


    class Config:
        from_attributes = True


class CreateUser(BaseUser):
    """ This is a schema to create a user account. """
    pass


class CreatedUserResponse(BaseUser):
    """ Response data for a newly created user. """

    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    role: str
    is_verified: bool
    hashed_password: str | None = Field(default=None, exclude=True)

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: str
    is_verified: bool
    role: str

class BaseAdminUser(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: validated_mobile_num
    password: str = Field(min_length=8)

class CreateAdminUser(BaseAdminUser):
    pass