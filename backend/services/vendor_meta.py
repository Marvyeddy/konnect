import uuid
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.constants.main import ReportStatus
from backend.models.reports import VendorReport
from backend.models.reviews import VendorReview
from backend.models.vendor_profile import VendorProfile
from backend.schemas.vendor_meta import ReportCreate, ReviewCreate


class VendorMetaService:
    async def add_vendor_review(
        self,
        buyer_id: uuid.UUID,
        vendor_id: uuid.UUID,
        review_data: ReviewCreate,
        session: AsyncSession,
    ) -> VendorReview:
        stmt = select(VendorReview).where(
            VendorReview.buyer_id == buyer_id, VendorReview.vendor_id == vendor_id
        )
        existing_review = (await session.execute(stmt)).scalar_one_or_none()
        if existing_review:
            raise HTTPException(
                status_code=400,
                detail="You have already submitted a review for this vendor.",
            )
        new_review = VendorReview(
            buyer_id=buyer_id,
            vendor_id=vendor_id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        session.add(new_review)
        await session.flush()
        avg_stmt = select(func.avg(VendorReview.rating)).where(
            VendorReview.vendor_id == vendor_id
        )
        calculated_avg = (await session.execute(avg_stmt)).scalar() or 3.0
        vendor_profile = await session.get(VendorProfile, vendor_id)
        if vendor_profile:
            vendor_profile.rating = round(float(calculated_avg), 2)
            session.add(vendor_profile)
        await session.commit()
        return new_review

    async def add_vendor_report(
        self,
        reporter_id: uuid.UUID,
        vendor_id: uuid.UUID,
        report_data: ReportCreate,
        session: AsyncSession,
    ) -> VendorReport:
        new_report = VendorReport(
            reporter_id=reporter_id,
            vendor_id=vendor_id,
            reason=report_data.reason,
            status=ReportStatus.PENDING,
        )
        session.add(new_report)
        await session.flush()
        vendor_profile = await session.get(VendorProfile, vendor_id)
        if vendor_profile:
            vendor_profile.report_count += 1
            session.add(vendor_profile)
        await session.commit()
        return new_report


vendor_meta_service = VendorMetaService()
