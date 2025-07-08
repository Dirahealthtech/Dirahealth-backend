from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, AsyncGenerator, List, Optional

from ..enums import UserRole
from ..exceptions import ForbiddenException, RevokedTokenException
from ..core.token_bearer import AccessTokenBearer
from ..db.database import AsyncSessionLocal
from ..models.user import User
from ..services import AuthService
from ..utils.auth import token_in_blacklist


auth_service = AuthService()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous dependency that provides a database session for FastAPI routes.

    Yields:
        AsyncSession: An instance of the asynchronous database session.

    Usage:
        Use as a dependency in FastAPI endpoints to access the database session.
        The session is automatically closed after the request is processed.
    """

    async with AsyncSessionLocal() as db:
        yield db
        await db.close()


async def get_current_user(
    token: dict = Depends(AccessTokenBearer()),
    session: AsyncSession = Depends(get_db),
):
    """
    Retrieve the current authenticated user based on the provided access token.

    Args:
        token (dict): A dictionary containing user information extracted from the access token.
        session (AsyncSession): The asynchronous database session dependency.

    Returns:
        User: The user object corresponding to the email found in the token.

    Raises:
        HTTPException: If the user cannot be found or the token is invalid.
    """
    jti = token.get("jti")

    # check if the access token is blacklisted
    if jti and await token_in_blacklist(jti, session):
        raise RevokedTokenException()


    user_email = token["user"]["email"]
    user = await auth_service.get_user(user_email, session)
    return user


async def get_anonymous_user(request: Request) -> Optional[User]:
    try:
        return await get_current_user(request)
    except Exception:
        return None


class RoleChecker:
    """
    Dependency class for FastAPI route protection using Role Based Access Control (RBAC).
    This class can be used as a dependency in FastAPI endpoints to restrict access to users
    with specific roles and to ensure that the user is verified.

    Args:
        allowed_roles (List[str]): A list of roles that are allowed to access the endpoint.

    Methods:
        __call__(current_user: User = Depends(get_current_user)) -> Any:
            Checks if the current user is verified and has one of the allowed roles.
            Raises HTTPException with status code 403 if the user is not verified or does not have the required role.
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles


    async def __call__(self, current_user: User = Depends(get_current_user)) -> Any:
        # Check if the user is verified
        if not current_user.is_verified:
            raise HTTPException(
                status_code=403,
                detail="User is not verified. Please verify your account to access this resource."
            )

        if current_user.role in self.allowed_roles:
            return True

        raise HTTPException(
            status_code=403,
            detail=f"You don't have the required role to access this endpoint!"
        )


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.role == UserRole.ADMIN:
        raise ForbiddenException(detail="Only admins can access this resource!")

    return user


def get_current_technician(user: User = Depends(get_current_user)) -> User:
    if not user.role == UserRole.SERVICE_TECH:
        raise ForbiddenException(detail="Only technicians can access this resource!")

    return user
