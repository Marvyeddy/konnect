from typing import Annotated
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.authorization import RoleChecker
from backend.constants.main import ReportStatus
from backend.dependencies import get_current_user
from backend.core.rate_limit import guard_decorator
from backend.external.database import get_session
from backend.models.users import Users
from backend.schemas.vendor_meta import ReportCreate, ReportRead, ReportReview
from backend.services.reports import ReportService

report_router = APIRouter()
report_service = ReportService()

admin = RoleChecker(["admin"])


@report_router.post("/{vendor_id}", status_code=status.HTTP_201_CREATED)
@guard_decorator.rate_limit(requests=5, window=3600)
async def submit_vendor_report(
    vendor_id: uuid.UUID,
    report_in: ReportCreate,
    current_user: Annotated[Users, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    report = await report_service.add_vendor_report(
        reporter_id=current_user.id,
        vendor_id=vendor_id,
        report_data=report_in,
        session=session,
    )
    return {"detail": "Report logged successfully.", "report_id": str(report.id)}


@report_router.get(
    "/review", response_model=list[ReportRead], dependencies=[Depends(admin)]
)
async def list_reports(
    session: Annotated[AsyncSession, Depends(get_session)],
    report_status: Annotated[ReportStatus | None, Query()] = None,
    vendor_id: Annotated[uuid.UUID | None, Query()] = None,
):
    return await report_service.list_reports(
        session=session, report_status=report_status, vendor_id=vendor_id
    )


@report_router.patch(
    "/tag/{report_id}", response_model=ReportRead, dependencies=[Depends(admin)]
)
async def review_report(
    report_id: uuid.UUID,
    review: ReportReview,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await report_service.review_report(
        report_id=report_id,
        new_status=review.status,
        session=session,
    )
