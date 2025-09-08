from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.exceptions import (
    create_exception_handler,
    AccessTokenRequiredException,
    AccountNotVerifiedException,
    CannotDeleteSupplier,
    CannotUpdateSupplierProfile,
    InvalidTokenException,
    InvalidUserCredentialsException,
    PasswordsDontMatchException,
    PasswordIsShortException,
    PermissionRequiredException,
    RefreshTokenRequiredException,
    RevokedTokenException,
    SupplierExistsException,
    SupplierNotFoundException,
    UserAlreadyExistsException,
    UsernameAlreadyExistsException,
    UserNotFoundException,
)
from app.middleware.auth_middleware import CustomAuthMiddleWare
from app.routers.appointments import router as appointments_router
from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.suppliers import router as suppliers_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as orders_router
from app.routers.user_activity import router as user_activity_router
from app.routers.reviews import router as reviews_router
from app.routers.homepage_sections import router as homepage_sections_router
from app.routers.user_management import router as user_management_router
from app.routers.mpesa import router as mpesa_router
from dotenv import load_dotenv

load_dotenv()

api_version = "v1"
swagger_docs_url = f"/api/{api_version}/docs"
redoc_docs_url = f"/api/{api_version}/redoc"
openapi_url = f"/api/{api_version}/openapi.json"

app = FastAPI(
    docs_url=swagger_docs_url,
    redoc_url=redoc_docs_url,
    openapi_url=openapi_url,  # This was missing!
    title="Dira Healthcare API",
    description="This is an ecommerce platform API focused on the medical device industry.",
    version="1.0.0",
    servers=[  # This was also missing!
        {
            "url": "https://app.dirahealthtech.co.ke",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ]
)

# Add CORS middleware first
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost', 
        'http://localhost:3000',
        'https://app.dirahealthtech.co.ke',  # Backend domain
        'https://dirahealthtech.co.ke',      # Root domain
        'https://www.dirahealthtech.co.ke',  # WWW version
        # Add your frontend domain here if it's different
        # 'https://your-frontend-domain.com',
    ],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allow_headers=["*"],
)

# Add custom auth middleware after CORS (order matters!)
app.add_middleware(CustomAuthMiddleWare)    # custom authentication middleware

# Register endpoints
app.include_router(auth_router, prefix=f'/api/{api_version}/auth', tags=["Authentication"])
app.include_router(admin_router, prefix=f'/api/{api_version}/admin', tags=["Admin"])
app.include_router(suppliers_router, prefix=f'/api/{api_version}/suppliers', tags=["Suppliers"])
app.include_router(appointments_router, prefix=f'/api/{api_version}/appointments', tags=["Appointments"])
app.include_router(cart_router, prefix=f'/api/{api_version}/cart', tags=["Cart"])
app.include_router(orders_router, prefix=f'/api/{api_version}/orders', tags=['Orders'])
app.include_router(user_activity_router, prefix=f'/api/{api_version}/user', tags=["User Activity"])
app.include_router(reviews_router, prefix=f'/api/{api_version}/reviews', tags=["Reviews"])
app.include_router(homepage_sections_router, prefix=f'/api/{api_version}', tags=["Homepage Sections"])
app.include_router(user_management_router, prefix=f'/api/{api_version}', tags=["User Management"])
app.include_router(mpesa_router, prefix=f'/api/{api_version}', tags=["M-Pesa Payments"])

# Add a root endpoint for health check
@app.get("/")
async def root():
    return {
        "message": "Dira Healthcare API",
        "version": "1.0.0",
        "docs": f"https://app.dirahealthtech.co.ke{swagger_docs_url}",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Register custom exceptions

# Auth-related exception handlers
app.add_exception_handler(AccessTokenRequiredException, create_exception_handler(403, "Authentication required!"))
app.add_exception_handler(AccountNotVerifiedException, create_exception_handler(403, "Please check your email and verify your account to use the app."))
app.add_exception_handler(PermissionRequiredException, create_exception_handler(403, "You don't have permission to access this resource."))
app.add_exception_handler(RefreshTokenRequiredException, create_exception_handler(401, "Please provide a refresh token."))
app.add_exception_handler(RevokedTokenException,create_exception_handler(401, "This token was revoked! Please login again."))
app.add_exception_handler(InvalidTokenException, create_exception_handler(401, "Invalid to expired token provided!"))
app.add_exception_handler(InvalidUserCredentialsException, create_exception_handler(400, "Invalid user credentials."))
app.add_exception_handler(PasswordsDontMatchException, create_exception_handler(400, "Passwords don't match!"))
app.add_exception_handler(PasswordIsShortException, create_exception_handler(400, "Password is too short!"))

# User-related exception handlers
app.add_exception_handler(UserAlreadyExistsException, create_exception_handler(409, "User with this email exists!"))
app.add_exception_handler(UsernameAlreadyExistsException, create_exception_handler(409, "The username is already taken!"))
app.add_exception_handler(UserNotFoundException, create_exception_handler(404, "User not found."))

# Supplier-related exception handlers
app.add_exception_handler(SupplierExistsException, create_exception_handler(409, "The supplier provided supplies your products!"))
app.add_exception_handler(SupplierNotFoundException, create_exception_handler(404, "Supplier not found!"))
app.add_exception_handler(CannotUpdateSupplierProfile, create_exception_handler(403, "You can't update a supplier who doesn't supply your products!"))
app.add_exception_handler(CannotDeleteSupplier, create_exception_handler(403, "You can't delete a supplier who doesn't supply your products!"))