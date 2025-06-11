from fastapi import Request
from fastapi.security import HTTPBearer
from fastapi.security.http import HTTPAuthorizationCredentials

from .. import exceptions
from ..utils.auth import decode_access_token


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
            raise exceptions.InvalidTokenException()

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
            raise exceptions.AccessTokenRequiredException()


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
            raise exceptions.RefreshTokenRequiredException()
