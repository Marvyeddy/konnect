import cloudinary
from fastapi import FastAPI
from guard import SecurityConfig
from guard.middleware import SecurityMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.core.config import config as cfg
from backend.errors import require_error
from backend.internal.admin import admin_router
from backend.middleware import require_middleware
from backend.routers.auth import auth_router
from backend.routers.notifications import notification_router
from backend.routers.onboarding import onboarding_router
from backend.routers.products import product_router
from backend.routers.users import user_router
from backend.routers.vendors import vendor_router

version = "v1"

app = FastAPI(
    title="konnect",
    description="A consumer-to-consumer (C2C) platform enabling direct exchange of goods, services, or information.",
    version=version,
    redoc_url=f"/api/{version}/redoc",
    docs_url=f"/api/{version}/docs",
    contact={
        "name": "Marvelous Anyatonwu",
        "url": "https://linkedin.com/in/anyatonwumarvelous",
        "email": "anyatonwumarvelous32@gmail.com",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
)

require_middleware(app)
require_error(app)

security_config = SecurityConfig(enable_redis=False, enable_rate_limiting=True)

app.add_middleware(
    SessionMiddleware,
    secret_key="8307760cd31789496c79a3801170c7c4578887628b04c3a12aa13cf32366c073",
    same_site="lax",
    https_only=False,
)

app.add_middleware(SecurityMiddleware, config=security_config)

# cloudinary setup
cloudinary.config(
    cloud_name=cfg.CLOUDINARY_CLOUD_NAME,
    api_key=cfg.CLOUDINARY_API_KEY,
    api_secret=cfg.CLOUDINARY_API_SECRET,
    secure=True,
)


@app.get("/")
async def root():
    return {"message": "Welcome to the konnect app"}


app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["Auth"])
app.include_router(
    onboarding_router, prefix=f"/api/{version}/onboarding", tags=["Onboarding"]
)
app.include_router(user_router, prefix=f"/api/{version}/users", tags=["Users"])
app.include_router(admin_router, prefix=f"/api/{version}/admin", tags=["Admin"])
app.include_router(vendor_router, prefix=f"/api/{version}/vendors", tags=["Vendor"])
app.include_router(
    notification_router, prefix=f"/api/{version}/notifications", tags=["Notification"]
)
app.include_router(product_router, prefix=f"/api/{version}/products", tags=["Product"])
