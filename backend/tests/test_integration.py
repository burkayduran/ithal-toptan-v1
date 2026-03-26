"""
Integration tests for:
  1. Register → login → /me flow
  2. Authenticated GET /campaigns/my (v2)
  3. Campaign join via v2 endpoint
  4. payment_collecting state machine transition
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Campaign,
    CampaignParticipant,
    Product,
    SupplierOffer,
)
from app.services.moq_service import MoQService

from tests.conftest import auth_headers, login_user, register_user

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _create_campaign(
    db: AsyncSession,
    status: str = "active",
    moq: int = 10,
) -> tuple[Campaign, Product, SupplierOffer]:
    """Create a Product + Campaign + SupplierOffer in the test DB."""
    product = Product(
        title=f"Test Product {uuid.uuid4().hex[:6]}",
        description="Integration test product",
        images=[],
    )
    db.add(product)
    await db.flush()

    campaign = Campaign(
        product_id=product.id,
        status=status,
        moq=moq,
        selling_price_try_snapshot=Decimal("500.00"),
        unit_price_usd_snapshot=Decimal("10.00"),
        supplier_name_snapshot="Test Supplier",
    )
    db.add(campaign)
    await db.flush()

    offer = SupplierOffer(
        campaign_id=campaign.id,
        supplier_name="Test Supplier",
        unit_price_usd=Decimal("10.00"),
        moq=moq,
        lead_time_days=14,
        selling_price_try=Decimal("500.00"),
        is_selected=True,
    )
    db.add(offer)
    await db.flush()

    campaign.selected_offer_id = offer.id
    await db.commit()
    await db.refresh(campaign)
    await db.refresh(product)
    await db.refresh(offer)
    return campaign, product, offer


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Register → Login → /me
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthFlow:
    async def test_register_returns_token(self, client: AsyncClient):
        resp = await client.post("/api/v1/auth/register", json={
            "email": f"user_{uuid.uuid4().hex[:8]}@test.com",
            "password": "StrongPass123!",
            "full_name": "İntegrasyon Test",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_duplicate_email_rejected(self, client: AsyncClient):
        email = f"dup_{uuid.uuid4().hex[:8]}@test.com"
        await client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "full_name": "First"
        })
        resp = await client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "full_name": "Second"
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    async def test_login_with_valid_credentials(self, client: AsyncClient):
        email = f"login_{uuid.uuid4().hex[:8]}@test.com"
        password = "LoginPass456!"
        await register_user(client, email, password)

        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_login_wrong_password_rejected(self, client: AsyncClient):
        email = f"wp_{uuid.uuid4().hex[:8]}@test.com"
        await register_user(client, email, "CorrectPass1!")
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPass"})
        assert resp.status_code == 401

    async def test_me_returns_user_profile(self, client: AsyncClient):
        email = f"me_{uuid.uuid4().hex[:8]}@test.com"
        full_name = "Mehmet Yılmaz"
        token = (await client.post("/api/v1/auth/register", json={
            "email": email, "password": "MePass789!", "full_name": full_name
        })).json()["access_token"]

        resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert data["full_name"] == full_name
        assert data["is_active"] is True

    async def test_me_without_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_me_with_invalid_token_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Authenticated GET /campaigns/my (v2)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCampaignsMy:
    async def test_campaigns_my_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v2/campaigns/my")
        assert resp.status_code == 401

    async def test_campaigns_my_empty_for_new_user(self, client: AsyncClient):
        email = f"wl_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WLPass123!"))["access_token"]

        resp = await client.get("/api/v2/campaigns/my", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_campaigns_my_shows_joined_campaigns(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wljoin_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WLJoin1!"))["access_token"]

        campaign, product, _ = await _create_campaign(db_session, status="active", moq=5)

        with patch("app.api.v2.campaigns.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.sync_counter_from_db = AsyncMock(return_value=1)
            instance.check_and_trigger = AsyncMock(return_value={
                "threshold_met": False, "transition_performed": False, "status_after": "active"
            })

            join_resp = await client.post(
                f"/api/v2/campaigns/{campaign.id}/join",
                json={"quantity": 2},
                headers=auth_headers(token),
            )
        assert join_resp.status_code in (200, 201), f"Join failed: {join_resp.text}"

        my_resp = await client.get("/api/v2/campaigns/my", headers=auth_headers(token))
        assert my_resp.status_code == 200
        items = my_resp.json()
        assert len(items) >= 1
        assert items[0]["campaign_id"] == str(campaign.id)
        assert items[0]["quantity"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 3. payment_collecting state machine transition
# ═══════════════════════════════════════════════════════════════════════════════

class TestPaymentCollectingTransition:
    async def _make_moq_service(self, db: AsyncSession) -> MoQService:
        redis_mock = MagicMock()
        redis_mock.get = AsyncMock(return_value=None)
        redis_mock.set = AsyncMock()
        redis_mock.publish = AsyncMock()
        redis_mock.eval = AsyncMock(return_value=1)
        return MoQService(db, redis_mock)

    async def test_moq_reached_transitions_to_payment_collecting_on_deadline(
        self, db_session: AsyncSession
    ):
        """
        process_expired_entries must transition campaign from moq_reached → payment_collecting
        before marking invited entries as expired.
        """
        campaign, product, offer = await _create_campaign(db_session, status="moq_reached", moq=2)

        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.execute(
            update(Campaign)
            .where(Campaign.id == campaign.id)
            .values(moq_reached_at=past_deadline - timedelta(hours=48), payment_deadline=past_deadline)
        )

        # Add an invited participant past their deadline
        participant = CampaignParticipant(
            campaign_id=campaign.id,
            user_id=uuid.uuid4(),
            quantity=1,
            status="invited",
            invited_at=past_deadline - timedelta(hours=48),
            payment_deadline=past_deadline,
        )
        db_session.add(participant)
        await db_session.commit()

        moq_svc = await self._make_moq_service(db_session)
        await moq_svc.process_expired_entries(campaign.id)

        refreshed = await db_session.execute(
            select(Campaign).where(Campaign.id == campaign.id)
        )
        updated_campaign = refreshed.scalar_one()

        # With 0 paid entries (< moq=2), it should reset to active after payment_collecting
        assert updated_campaign.status == "active", (
            f"Expected 'active' after reset, got '{updated_campaign.status}'"
        )

    async def test_trigger_payment_phase_sets_moq_reached(self, db_session: AsyncSession):
        """trigger_payment_phase must transition active → moq_reached."""
        campaign, product, offer = await _create_campaign(db_session, status="active", moq=2)

        moq_svc = await self._make_moq_service(db_session)

        with patch("app.tasks.email_tasks.send_moq_reached_email") as mock_email, \
             patch("app.tasks.moq_tasks.cleanup_expired_entries") as mock_cleanup:
            mock_email.delay = MagicMock()
            mock_cleanup.apply_async = MagicMock()
            result = await moq_svc.trigger_payment_phase(campaign.id, campaign)

        assert result is True

        refreshed = await db_session.execute(
            select(Campaign).where(Campaign.id == campaign.id)
        )
        updated = refreshed.scalar_one()
        assert updated.status == "moq_reached"
        assert updated.payment_deadline is not None

    async def test_payment_collecting_to_ordered_when_enough_paid(self, db_session: AsyncSession):
        """
        When paid_count >= moq after the deadline, campaign must go
        payment_collecting → ordered.
        """
        campaign, product, offer = await _create_campaign(db_session, status="moq_reached", moq=1)

        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.execute(
            update(Campaign)
            .where(Campaign.id == campaign.id)
            .values(moq_reached_at=past_deadline - timedelta(hours=48), payment_deadline=past_deadline)
        )

        # Add a PAID participant — satisfies the moq
        paid_participant = CampaignParticipant(
            campaign_id=campaign.id,
            user_id=uuid.uuid4(),
            quantity=1,
            status="paid",
        )
        db_session.add(paid_participant)
        await db_session.commit()

        moq_svc = await self._make_moq_service(db_session)
        await moq_svc.process_expired_entries(campaign.id)

        refreshed = await db_session.execute(
            select(Campaign).where(Campaign.id == campaign.id)
        )
        updated = refreshed.scalar_one()
        assert updated.status == "ordered", (
            f"Expected 'ordered' when paid_count >= moq, got '{updated.status}'"
        )
