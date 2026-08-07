from fastapi import FastAPI
from guard import SecurityConfig, SecurityMiddleware

from backend.middleware import require_middleware
from backend.routers.auth import auth_router

version = "v1"
app = FastAPI(
    title="konnect",
    description="An app to connect vendors and buyers with ease",
    version=version,
    docs_url=f"/api/{version}/docs",
    redoc_url=f"/api/{version}/redoc",
)

require_middleware(app)

config = SecurityConfig(enable_rate_limiting=True, enable_redis=False)
app.add_middleware(SecurityMiddleware, config=config)


@app.get("/")
async def root():
    return {"message": "Konnect started"}


app.include_router(auth_router, prefix=f"/api/{version}/auth", tags=["auth"])
