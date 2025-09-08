from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


api_version = 'v1'


class CustomAuthMiddleWare(BaseHTTPMiddleware):
    """
    Custom authentication middleware for FastAPI applications.
    This middleware intercepts incoming HTTP requests and enforces authentication
    for protected routes. It allows unauthenticated access to specific endpoints
    such as documentation and authentication-related routes (login, signup, etc.).
    For all other routes, it checks for the presence of the "Authorization" header.
    If the header is missing, it returns a 401 Unauthorized response.

    Methods
    -------
    dispatch(request: Request, call_next):
        Processes each incoming request, allowing or denying access based on the
        request path and authentication headers.
    """

    async def dispatch(self, request: Request, call_next):
        # Always allow OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Allow unauthenticated access to specific routes
        path = request.url.path.rstrip("/")

        allowed_paths = [
            # Root and health endpoints
            "",  # Empty string for root path
            "/health",
            "/favicon.ico",
            
            # Documentation endpoints
            "/openapi.json",
            f"/api/{api_version}/openapi.json", 
            f"/api/{api_version}/docs",
            f"/api/{api_version}/redoc",
            
            # Authentication endpoints
            f"/api/{api_version}/auth/login",
            f"/api/{api_version}/auth/signup",
            f"/api/{api_version}/auth/request-verification-link",
            f"/api/{api_version}/auth/verify-account",
            f"/api/{api_version}/auth/reset-password",
            f"/api/{api_version}/auth/confirm-reset-password",
            
            # Admin endpoints
            f"/api/{api_version}/admin/setup-initial-admin",
            f"/api/{api_version}/admin/list-categories",
            f"/api/{api_version}/admin/list-products",
            f"/api/{api_version}/admin/get-products",
            
            # Public endpoints
            f"/api/{api_version}/reviews/product",
            f"/api/{api_version}/homepage-sections",
            f"/api/{api_version}/user/activity/homepage",
            f"/api/{api_version}/user/activity/top-picks",
            f"/api/{api_version}/user/activity/product"
        ]

        # Check if path is allowed
        if any(path == prefix or path.startswith(prefix + "/") for prefix in allowed_paths):
            return await call_next(request)

        
        if "Authorization" not in request.headers:
            return JSONResponse(
                content={
                    "message": "Not authenticated! Please login again to proceed.",
                },
                status_code=401
            )

        response = await call_next(request)
        return response