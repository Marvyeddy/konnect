import uuid
import pytest
from unittest.mock import patch
from fastapi import status
from backend.main import app
from backend.dependencies import get_current_user
from backend.models.users import Users
from backend.models.vendor_profile import VendorProfile
from backend.schemas.vendor_meta import ReviewCreate, ReportCreate
from backend.services.vendor_meta import vendor_meta_service

TEST_BUYER_ID = uuid.uuid4()
TEST_VENDOR_PROFILE_ID = uuid.uuid4()
TEST_VENDOR_USER_ID = uuid.uuid4()


@pytest.fixture
def mock_buyer_auth(session):
    import asyncio

    buyer = Users(
        id=TEST_BUYER_ID,
        email="buyer_reviewer@email.com",
        username="buyer_reviewer",
        password="hashed_password",
        role="buyer",
    )

    shop_owner = Users(
        id=TEST_VENDOR_USER_ID,
        email="shop_owner@email.com",
        username="shop_owner",
        password="hashed_password",
        role="vendor",
    )

    vendor_profile = VendorProfile(
        id=TEST_VENDOR_PROFILE_ID,
        user_id=shop_owner.id,
        full_name="John Vendor",
        business_name="Super Tech Store",
        phone_number="+23480000000",
        address="123 Tech Lane",
        rating=3.0,
        report_count=0,
        verified=True,
    )

    loop = asyncio.get_event_loop()

    async def _setup_db():
        session.add(buyer)
        session.add(shop_owner)
        session.add(vendor_profile)
        await session.commit()

    loop.run_until_complete(_setup_db())
    app.dependency_overrides[get_current_user] = lambda: buyer
    yield buyer
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_service_add_vendor_review_and_recalculate_average(
    session, mock_buyer_auth
):
    review_in_1 = ReviewCreate(rating=5, comment="Amazing customer service!")
    await vendor_meta_service.add_vendor_review(
        buyer_id=TEST_BUYER_ID,
        vendor_id=TEST_VENDOR_PROFILE_ID,
        review_data=review_in_1,
        session=session,
    )

    profile = await session.get(VendorProfile, TEST_VENDOR_PROFILE_ID)
    assert profile.rating == 5.0

    another_buyer = Users(
        id=uuid.uuid4(), email="b2@email.com", username="b2", password="p"
    )
    session.add(another_buyer)
    await session.commit()

    review_in_2 = ReviewCreate(rating=3, comment="Decent experience.")
    await vendor_meta_service.add_vendor_review(
        buyer_id=another_buyer.id,
        vendor_id=TEST_VENDOR_PROFILE_ID,
        review_data=review_in_2,
        session=session,
    )

    await session.refresh(profile)
    assert profile.rating == 4.0


@pytest.mark.asyncio
async def test_service_add_vendor_report_increments_counter(session, mock_buyer_auth):
    report_in = ReportCreate(reason="Vendor is shipping defective counterfeits.")

    await vendor_meta_service.add_vendor_report(
        reporter_id=TEST_BUYER_ID,
        vendor_id=TEST_VENDOR_PROFILE_ID,
        report_data=report_in,
        session=session,
    )

    profile = await session.get(VendorProfile, TEST_VENDOR_PROFILE_ID)
    assert profile.report_count == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_buyer_auth")
async def test_router_submit_review_success(client):
    payload = {"rating": 4, "comment": "Item arrived exactly as described."}

    response = await client.post(
        f"/api/v1/vendors/{TEST_VENDOR_PROFILE_ID}/reviews", json=payload
    )

    assert response.status_code == 201
    assert response.json()["detail"] == "Review submitted successfully."


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_buyer_auth")
async def test_router_submit_review_validation_error(client):
    payload = {"rating": 6, "comment": "Unbelievably good"}

    response = await client.post(
        f"/api/v1/vendors/{TEST_VENDOR_PROFILE_ID}/reviews", json=payload
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_router_cannot_review_own_profile(client, session, mock_buyer_auth):
    owner = await session.get(Users, TEST_VENDOR_USER_ID)
    app.dependency_overrides[get_current_user] = lambda: owner

    payload = {"rating": 5, "comment": "Boosting my own storefront metrics!"}
    response = await client.post(
        f"/api/v1/vendors/{TEST_VENDOR_PROFILE_ID}/reviews", json=payload
    )

    assert response.status_code == 400
    assert "cannot review your own" in response.json()["detail"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_buyer_auth")
async def test_router_submit_report_success(client):
    payload = {
        "reason": "The vendor refuses to fulfill refunds for broken inventory items."
    }

    response = await client.post(
        f"/api/v1/vendors/{TEST_VENDOR_PROFILE_ID}/reports", json=payload
    )

    assert response.status_code == 201
    assert response.json()["detail"] == "Report logged successfully."
