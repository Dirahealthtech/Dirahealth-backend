from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from typing import Any, Callable


class APIException(Exception):
    """ Base class for all exceptions in the Tushare API. """
    pass


class InvalidTokenException(APIException):
    """ Exception is thrown when user provided an expired invalid token. """
    pass


class RevokedTokenException(APIException):
    """ Exception is raised when a user has provided a revoked token. """
    pass


class AccessTokenRequiredException(APIException):
    """ Exception is raised when a user has provided an refresh token instead of an access token. """
    pass


class RefreshTokenRequiredException(APIException):
    """ Exception is raised when a user has provided an access token instead of a refresh token. """
    pass


class InvalidUserCredentialsException(APIException):
    """ Exception is thrown when a user has provided invalid credentials. """
    pass


class UserAlreadyExistsException(APIException):
    """ Exception is thrown when a user has provided an email that exists. """
    pass


class UsernameAlreadyExistsException(APIException):
    """ Exception is thrown when a user has provided a username that exists. """
    pass


class PermissionRequiredException(APIException):
    """ Exception is thrown when a user does not have permission to peform the current action or access an endpoint/resource. """
    pass


class AccountNotVerifiedException(APIException):
    """ Exception is thrown when a user tries to perform an action without verifying their account. """
    pass


class UserNotFoundException(APIException):
    """ Exception is thrown when a user is not found. """
    pass


class PasswordIsShortException(APIException):
    """ Exception is raised when password and confirm password is short. """
    pass


class PasswordsDontMatchException(APIException):
    """ Exception is raised if the password and confirm password don't match. """
    pass


class SupplierExistsException(APIException):
    """ Exception is raised if the admin adds duplicate supplier. """
    pass


class SupplierNotFoundException(APIException):
    """ Excpetion is raised if a supplier record is not found. """
    pass


class CannotUpdateSupplierProfile(APIException):
    """ Exception raised when the current user tries to update a supplier they didn't create. """
    pass


class CannotDeleteSupplier(APIException):
    """ Exception raised when the current user tries to update a supplier they didn't create. """
    pass


class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequestException(HTTPException):
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictException(HTTPException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


def create_exception_handler(status_code: int, detail: Any) -> Callable[[Request, Exception], JSONResponse]:
    async def exception_handler(request: Request, exception: APIException):
        return JSONResponse(
            content={"detail": detail},
            status_code=status_code
        )

    return exception_handler
