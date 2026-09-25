import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.constants.main import ReportStatus
from backend.models.reports import VendorReport
from backend.models.vendor_profile import VendorProfile
from backend.models.users import Users
from backend.models.notification import Notification  # adjust to your project
from backend.services.sse_manager import SSEConnectionManager  # adjust to your project
from backend.core.logging import get_app_logger  # adjust to your project
from backend.schemas.vendor_meta import ReportCreate

STRIKE_LIMIT = 3

notification_manager = SSEConnectionManager()
logger = get_app_logger(__name__)


class ReportService:
    @staticmethod
    async def add_vendor_report(
        reporter_id: uuid.UUID,
        vendor_id: uuid.UUID,
        report_data: ReportCreate,
        session: AsyncSession,
    ) -> VendorReport:
        vendor = await session.get(VendorProfile, vendor_id)
        if not vendor:
            raise HTTPException(status_code=404, detail="Vendor profile not found.")

        if vendor.user_id == reporter_id:
            raise HTTPException(
                status_code=400, detail="You cannot report your own vendor profile."
            )

        if not vendor.is_active:
            raise HTTPException(
                status_code=400, detail="This vendor is already under review."
            )

        report = VendorReport(
            reporter_id=reporter_id,
            vendor_id=vendor_id,
            reason=report_data.reason,
        )
        session.add(report)
        try:
            await session.commit()
        except IntegrityError:
            # UniqueConstraint(reporter_id, vendor_id) — duplicate report.
            await session.rollback()
            raise HTTPException(
                status_code=409, detail="You have already reported this vendor."
            )
        await session.refresh(report)
        return report

    @staticmethod
    async def count_approved_reports(
        vendor_id: uuid.UUID, session: AsyncSession
    ) -> int:
        result = await session.scalar(
            select(func.count(VendorReport.id)).where(
                VendorReport.vendor_id == vendor_id,
                VendorReport.status == ReportStatus.APPROVED,
            )
        )
        return result or 0

    @staticmethod
    async def review_report(
        report_id: uuid.UUID,
        new_status: ReportStatus,
        session: AsyncSession,
    ) -> VendorReport:
        if new_status == ReportStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Cannot set a report back to pending. Use approved or dismissed.",
            )

        report = await session.get(VendorReport, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        if report.status != ReportStatus.PENDING:
            raise HTTPException(
                status_code=409, detail="This report has already been reviewed."
            )

        report.status = new_status
        report.reviewed_at = datetime.now(UTC)
        session.add(report)
        await session.flush()

        vendor_deactivated = False
        strike_count = 0
        if new_status == ReportStatus.APPROVED:
            strike_count = await ReportService.count_approved_reports(
                report.vendor_id, session
            )
            if strike_count >= STRIKE_LIMIT:
                vendor = await session.get(VendorProfile, report.vendor_id)
                if vendor and vendor.is_active:
                    vendor.is_active = False
                    session.add(vendor)
                    vendor_deactivated = True

        await session.commit()
        await session.refresh(report)

        # Notifications — must never break the review flow itself.
        try:
            if vendor_deactivated:
                vendor = await session.get(VendorProfile, report.vendor_id)
                await ReportService._notify_admins_vendor_deactivated(
                    vendor=vendor,
                    strikes=strike_count,
                    report=report,
                    session=session,
                )
                await ReportService._notify_vendor_deactivated(
                    vendor=vendor,
                    strikes=strike_count,
                    session=session,
                )
        except Exception as log_err:
            logger.error(f"Notification broadcasting failed: {log_err}")

        return report

    @staticmethod
    async def list_reports(
        session: AsyncSession,
        report_status: ReportStatus | None = None,
        vendor_id: uuid.UUID | None = None,
    ) -> list[VendorReport]:
        query = select(VendorReport).order_by(VendorReport.created_at.desc())
        if report_status is not None:
            query = query.where(VendorReport.status == report_status)
        if vendor_id is not None:
            query = query.where(VendorReport.vendor_id == vendor_id)
        result = await session.scalars(query)
        return list(result.all())

    # ---------------------------------------------------------------------------
    # Notifications
    # ---------------------------------------------------------------------------
    @staticmethod
    async def _get_admin_ids(session: AsyncSession) -> list[str]:
        admin_query = await session.execute(
            select(Users.id).where(Users.role == "admin")
        )
        return [str(row[0]) for row in admin_query.all()]

    @staticmethod
    async def _notify_admins_vendor_deactivated(
        vendor: VendorProfile,
        strikes: int,
        report: VendorReport,
        session: AsyncSession,
    ) -> None:
        admin_ids = await ReportService._get_admin_ids(session)
        if not admin_ids:
            return

        msg_title = "Vendor deactivated after multiple approved reports"
        msg_body = (
            f"Vendor '{vendor.business_name}' was automatically deactivated after "
            f"{strikes} approved reports."
        )

        notifications_to_add = [
            Notification(
                user_id=admin_id,
                title=msg_title,
                message=msg_body,
                notification_type="VENDOR_DEACTIVATED",
                action_url=f"/admin/vendors/{vendor.id}",
                is_read=False,
            )
            for admin_id in admin_ids
        ]
        session.add_all(notifications_to_add)
        await session.commit()

        live_payload = {
            "title": msg_title,
            "message": msg_body,
            "notification_type": "VENDOR_DEACTIVATED",
            "action_url": f"/admin/vendors/{vendor.id}",
            "vendor_id": str(vendor.id),
            "report_id": str(report.id),
            "strike_count": strikes,
        }
        await notification_manager.broadcast_to_admins(admin_ids, live_payload)

    @staticmethod
    async def _notify_vendor_deactivated(
        vendor: VendorProfile,
        strikes: int,
        session: AsyncSession,
    ) -> None:
        msg_title = "Your vendor account has been deactivated"
        msg_body = (
            f"Your vendor profile '{vendor.business_name}' has been deactivated after "
            f"{strikes} verified reports from users. If you believe this is a mistake, "
            f"please contact support."
        )

        session.add(
            Notification(
                user_id=str(vendor.user_id),
                title=msg_title,
                message=msg_body,
                notification_type="VENDOR_DEACTIVATED",
                action_url="/vendor/appeal",  # adjust to your appeal/contact route
                is_read=False,
            )
        )
        await session.commit()

        live_payload = {
            "title": msg_title,
            "message": msg_body,
            "notification_type": "VENDOR_DEACTIVATED",
            "action_url": "/vendor/appeal",
            "vendor_id": str(vendor.id),
            "strike_count": strikes,
        }
        await notification_manager.broadcast(str(vendor.user_id), live_payload)
