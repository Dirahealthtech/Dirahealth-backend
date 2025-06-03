from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio.session import AsyncSession

from .. import exceptions
from ..models import User
from ..schemas import CreateUser
from ..utils.auth import hash_password
from ..enums import UserRole


class AuthService:
    """
    Service class for handling user authentication and account management.
    """

    async def get_user(self, email: str, db: AsyncSession):
        """
        Asynchronously retrieves a user from the database by matching the provided email address.
        """

        stmt = select(User).where(User.email==email)
        user = (await db.execute(stmt)).scalars().first()

        if not user:
            raise exceptions.UserNotFoundException()

        return user


    async def user_exists(self, email: str, db: AsyncSession) -> bool:
        """
        Check if a user with the given email exists in the database.
        """

        user = await self.get_user(email, db)
        return True if user else False


    async def create_user_account(self, user: CreateUser, db: AsyncSession):
        """ Creates a new user account. """

        user_data = user.model_dump()

        user_email = user_data["email"]
        user_exists = await self.user_exists(user_email, db)

        if user_exists:
            raise exceptions.UserAlreadyExistsException()

        hashed_password = hash_password(user.hashed_password)

        # replace "password" in user_data with the hashed password
        user_data['hashed_password'] = hashed_password

        db_user = User(**user_data)

        try:
            db.add(db_user)
            await db.commit()
            await db.refresh(db_user)

            return db_user

        except IntegrityError as e:
            await db.rollback()  # Rollback the transaction to avoid issues

            # Check if the error is due to a unique constraint violation - user account already exists
            if "UNIQUE constraint failed" in str(e.orig):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already exists. Please choose a different one."
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unexpected database error occurred: {str(e)}"
            )


    async def update_user_profile(self, user: User, user_data: dict, session: AsyncSession):
        """
        Asynchronously updates the profile information of a user with the provided data.
        """

        for key, value in user_data.items():
            setattr(user, key, value)

        await session.commit()
        return user


    async def create_admin_user(self, user: CreateUser, role: UserRole, db: AsyncSession):
        """
        Create a user with a specific role (admin function)
        """
        user_email = user.email.lower()
        
        # Check if user already exists
        user_exists = await self.user_exists(user_email, db)
        if user_exists:
            raise exceptions.UserAlreadyExistsException()
        hashed_password = hash_password(user.password)
        
        new_user = User(
            email=user_email,
            hashed_password=hashed_password,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            role=role,
            is_verified=True
        )
        
        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user
        except IntegrityError:
            await db.rollback()
            raise exceptions.UserAlreadyExistsException()
