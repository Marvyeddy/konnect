from fastapi import FastAPI
from guard import SecurityConfig
from guard.middleware import SecurityMiddleware

from backend.errors import require_error
from backend.middleware import require_middleware
from backend.routers.auth import auth_router

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

app.add_middleware(SecurityMiddleware, config=security_config)


@app.get("/")
async def root():
    return {"message": "Welcome to the konnect app"}


app.include_router(auth_router, prefix="/api/{version}/auth", tags=["Auth"])
