from fastapi import APIRouter

onboarding_router = APIRouter()


@onboarding_router.post("/user")
async def onboard_user():
    pass
