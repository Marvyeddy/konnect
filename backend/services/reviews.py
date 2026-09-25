import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.models.reviews import VendorReview
from backend.models.vendor_profile import VendorProfile
from backend.schemas.vendor_meta import ReviewCreate


class VendorReviewService:
    @staticmethod
    async def add_vendor_review(
        buyer_id: uuid.UUID,
        vendor_id: uuid.UUID,
        review_data: ReviewCreate,
        session: AsyncSession,
    ) -> VendorReview:
        vendor = await session.get(VendorProfile, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor profile not found.")

        if vendor.user_id == buyer_id:
            raise HTTPException(
                status_code=400, detail="You cannot review your own vendor profile."
            )

        if not vendor.is_active:
            raise HTTPException(
                status_code=400, detail="This vendor is no longer active."
            )

        review = VendorReview(
            buyer_id=buyer_id,
            vendor_id=vendor_id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        session.add(review)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=409, detail="You have already reviewed this vendor."
            )
        await session.refresh(review)
        return review

    @staticmethod
    async def get_vendor_rating(
        vendor_id: uuid.UUID, session: AsyncSession
    ) -> float | None:
        """
        Compute vendor's average rating and update the denormalized value
        in VendorProfile.rating. Returns None if no reviews yet.
        """
        avg = await session.scalar(
            select(func.avg(VendorReview.rating)).where(
                VendorReview.vendor_id == vendor_id
            )
        )
        if avg is not None:
            avg_rounded = round(avg, 2)
            # Update denormalized rating column on VendorProfile
            vendor_profile = await session.get(VendorProfile, vendor_id)
            if vendor_profile:
                vendor_profile.rating = avg_rounded
                session.add(vendor_profile)
                await session.commit()
            return avg_rounded
        else:
            # Optionally, set to default if no reviews
            vendor_profile = await session.get(VendorProfile, vendor_id)
            if vendor_profile:
                vendor_profile.rating = 3.0  # or other default as your model
                session.add(vendor_profile)
                await session.commit()
            return None

    @staticmethod
    async def count_vendor_reviews(vendor_id: uuid.UUID, session: AsyncSession) -> int:
        result = await session.scalar(
            select(func.count(VendorReview.id)).where(
                VendorReview.vendor_id == vendor_id
            )
        )
        return result or 0

    @staticmethod
    async def list_vendor_reviews(
        vendor_id: uuid.UUID, session: AsyncSession
    ) -> list[VendorReview]:
        result = await session.scalars(
            select(VendorReview)
            .where(VendorReview.vendor_id == vendor_id)
            .order_by(VendorReview.created_at.desc())
        )
        return list(result.all())
