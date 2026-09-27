from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies import get_current_user
from backend.core.rate_limit import guard_decorator
from backend.external.database import get_session
from backend.models.users import Users
from backend.routers.vendors import review_service
from backend.schemas.vendor_meta import ReviewCreate, ReviewRead

review_router = APIRouter()


@review_router.post("/{vendor_id}", status_code=status.HTTP_201_CREATED)
@guard_decorator.rate_limit(requests=10, window=3600)
async def submit_vendor_review(
    vendor_id: uuid.UUID,
    review_in: ReviewCreate,
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    review = await review_service.add_vendor_review(
        buyer_id=current_user.id,
        vendor_id=vendor_id,
        review_data=review_in,
        session=session,
    )
    return {"detail": "Review submitted successfully.", "review_id": str(review.id)}


@review_router.get("/{vendor_id}", response_model=list[ReviewRead])
async def list_vendor_reviews(
    vendor_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await review_service.list_vendor_reviews(
        vendor_id=vendor_id, session=session
    )
