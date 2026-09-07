from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.external.database import get_session
from backend.models.users import Users
from backend.schemas.vendors import UserOut

vendor_router = APIRouter()


@vendor_router.get("/me", response_model=UserOut)
async def get_vendor_profile(
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to access this resource.",
        )
    return current_user


@vendor_router.patch("/me/update")
async def update_vendor_profile(
    vendor_data_str: Annotated[str, Form(alias="vendor_data")],
    image: Annotated[UploadFile | None, File()] = None,
    current_user: Annotated[Users | None, Depends(get_current_user)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
):
    pass
