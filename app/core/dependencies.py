from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, List

from ..db.database import AsyncGenerator, AsyncSessionLocal
from ..db.redis import token_in_blacklist
from ..models.user import User
from ..services.auth_service import AuthService
from ..utils.auth import decode_access_token


auth_service = AuthService()


class TokenBearer(HTTPBearer):
    """
    Custom HTTPBearer authentication class for FastAPI that validates and processes JWT access tokens.
    This class extends the HTTPBearer security scheme to:
    - Decode and validate JWT access tokens from the Authorization header.
    - Check if the token is valid and not blacklisted (revoked).
    - Enforce additional access token verification logic via the `verify_access_token` method, which must be implemented by subclasses.

    Methods:
        __init__(auto_error: bool = True):
            Initializes the TokenBearer with optional automatic error handling.
        async __call__(request: Request) -> HTTPAuthorizationCredentials | None:
            Processes the incoming request, extracts and decodes the JWT token, checks its validity and blacklist status,
            and calls the subclass-implemented verification method.
        token_valid(token: str) -> bool:
            Checks if the provided token can be successfully decoded.
        verify_access_token(token_data):
            Abstract method to be implemented by subclasses for additional token verification logic.

    Raises:
        HTTPException: If the token is invalid, revoked, or fails verification.
    """

    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)


    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        """
        Asynchronously validates and processes an HTTP authorization token from the request.

        Args:
            request (Request): The incoming HTTP request object.

        Returns:
            dict | None: The decoded token data if the token is valid, otherwise None.

        Raises:
            HTTPException: If the token is invalid or has been revoked.
        """

        creds = await super().__call__(request)
        token = creds.credentials
        token_data = decode_access_token(token)

        if not self.token_valid(token):
            raise HTTPException(
                status_code=403,
                detail="You have provided an invalid token",
            )

        if await token_in_blacklist(token_data["jti"]):
            raise HTTPException(
                status_code=403,
                detail="Token has been revoked. Please log in again."
            )

        self.verify_token(token_data)
        return token_data

    def token_valid(self, token: str) -> bool:
        """
        Validates the provided access token.
        Args:
            token (str): The access token to validate.
        Returns:
            bool: True if the token is valid, False otherwise.
        """

        token_data = decode_access_token(token)

        if token_data is None:
            return False

        return True

    def verify_token(self, token_data):
        """
        Verifies the provided access token data. This method should be implemented by subclasses to define the logic for
        validating the access token and extracting relevant information from it.

        Args:
            token_data: The data extracted from the access token to be verified.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.

        Returns:
            Any: The result of the token verification, as defined by the subclass.
        """

        raise NotImplementedError("Subclasses must implement this method.")


class AccessTokenBearer(TokenBearer):
    """
    A subclass of TokenBearer that provides additional verification for access tokens.

    Methods
    -------
    verify_access_token(token_data: dict)
        Verifies the provided token data to ensure it is an access token and not a refresh token.
        Raises an HTTPException with status code 403 if the token is identified as a refresh token.
    """

    def verify_token(self, token_data: dict):
        """
        Verifies the provided access token data.

        Args:
            token_data (dict): A dictionary containing token information.
                Expected to have a "refresh" key indicating if the token is a refresh token.
        Raises:
            HTTPException: If the token is a refresh token or authentication fails,
                raises an HTTP 403 error with an appropriate message.
        """

        if token_data and token_data["refresh"]:
            raise HTTPException(
                status_code=403,
                detail="Authentication failed! Please log in to your account."
            )


class RefreshTokenBearer(TokenBearer):
    """
    A custom token bearer class for handling refresh tokens.

    This class extends the TokenBearer class and provides additional verification to ensure
    that the provided token is a valid refresh token.

    Methods
    -------
    verify_access_token(token_data: dict)
        Verifies that the token data corresponds to a refresh token.
        Raises an HTTPException with status code 403 if the token is not a refresh token.
    """

    def verify_token(self, token_data: dict):
        """
        Verifies the provided access token data to ensure it is a valid refresh token.

        Args:
            token_data (dict): A dictionary containing token information.
                Expected to have a 'refresh' key indicating if the token is a refresh token.
        Raises:
            HTTPException: If the token is not a valid refresh token, raises an HTTP 403 error
                with a message prompting for a valid refresh token.
        """

        if token_data and not token_data["refresh"]:
            raise HTTPException(
                status_code=403,
                detail="Please provide a valid refresh token!"
            )


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

    user_email = token["user"]["email"]
    user = await auth_service.get_user(user_email, session)
    return user


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
