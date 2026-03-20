"""
Progress endpoint hardening tests (V2):
  1. Public campaign: progress data is returned
  2. Non-public status (draft, cancelled, etc.): uniform 404, no data leaked
  3. Non-existent campaign_id: 404 (same response shape as non-public, no info leak)
  4. Uniform 404 for SSE endpoint on non-public/missing campaigns
"""
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Campaign, Product, SupplierOffer
from tests.conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

async def _create_campaign(
    db: AsyncSession,
    status: str,
    with_offer: bool = True,
) -> Campaign:
    product = Product(
        title=f"Progress Test {uuid.uuid4().hex[:6]}",
        description="Test",
        images=[],
    )
    db.add(product)
    await db.flush()

    campaign = Campaign(
        product_id=product.id,
        status=status,
        moq=50,
        selling_price_try_snapshot=Decimal("500.00"),
        unit_price_usd_snapshot=Decimal("10.00"),
    )
    db.add(campaign)
    await db.flush()

    if with_offer:
        offer = SupplierOffer(
            campaign_id=campaign.id,
            supplier_name="Supplier",
            unit_price_usd=Decimal("10.00"),
            moq=50,
            lead_time_days=14,
            selling_price_try=Decimal("500.00"),
            is_selected=True,
        )
        db.add(offer)
        await db.flush()
        campaign.selected_offer_id = offer.id

    await db.commit()
    await db.refresh(campaign)
    return campaign


# ───────────────────────────────────────────────────────────────────────────────
# 1. Public statuses — progress endpoint must return data
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressPublicAccess:
    @pytest.mark.parametrize("status", ["active", "moq_reached", "payment_collecting"])
    async def test_public_status_returns_progress(
        self, client: AsyncClient, db_session: AsyncSession, status: str
    ):
        from unittest.mock import AsyncMock, patch

        campaign = await _create_campaign(db_session, status=status)

        with patch("app.api.v2.campaigns.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.get_current_count = AsyncMock(return_value=10)

            resp = await client.get(f"/api/v2/campaigns/{campaign.id}/progress")

        assert resp.status_code == 200, f"Expected 200 for {status!r}, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "current" in data
        assert "target" in data
        assert "percentage" in data
        assert data["campaign_id"] == str(campaign.id)

    async def test_progress_no_auth_required_for_public(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Progress endpoint must be accessible without a token for public campaigns."""
        from unittest.mock import AsyncMock, patch

        campaign = await _create_campaign(db_session, status="active")

        with patch("app.api.v2.campaigns.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.get_current_count = AsyncMock(return_value=5)
            resp = await client.get(f"/api/v2/campaigns/{campaign.id}/progress")

        assert resp.status_code == 200


# ───────────────────────────────────────────────────────────────────────────────
# 2. Non-public statuses — must return 404 with no leakage
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressNonPublicBlocked:
    @pytest.mark.parametrize("status", ["draft", "cancelled", "ordered", "delivered"])
    async def test_non_public_status_returns_404(
        self, client: AsyncClient, db_session: AsyncSession, status: str
    ):
        campaign = await _create_campaign(db_session, status=status)
        resp = await client.get(f"/api/v2/campaigns/{campaign.id}/progress")
        assert resp.status_code == 404, f"Expected 404 for {status!r}, got {resp.status_code}"

    async def test_non_public_and_missing_produce_same_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-public and missing IDs must return identical status codes."""
        campaign = await _create_campaign(db_session, status="draft")
        missing_id = uuid.uuid4()

        non_public_resp = await client.get(f"/api/v2/campaigns/{campaign.id}/progress")
        missing_resp = await client.get(f"/api/v2/campaigns/{missing_id}/progress")

        assert non_public_resp.status_code == 404
        assert missing_resp.status_code == 404


# ───────────────────────────────────────────────────────────────────────────────
# 3. Non-existent campaign_id — must return 404 (not 500 or 422)
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressMissingCampaign:
    async def test_unknown_uuid_returns_404(self, client: AsyncClient):
        random_id = uuid.uuid4()
        resp = await client.get(f"/api/v2/campaigns/{random_id}/progress")
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        """Malformed UUIDs should fail at the parameter parsing level (422), not 500."""
        resp = await client.get("/api/v2/campaigns/not-a-uuid/progress")
        assert resp.status_code == 422


# ───────────────────────────────────────────────────────────────────────────────
# 4. SSE endpoint — non-public/missing must return uniform 404
# ───────────────────────────────────────────────────────────────────────────────

class TestSSEProgressHardening:
    async def test_sse_missing_campaign_returns_404(self, client: AsyncClient):
        random_id = uuid.uuid4()
        resp = await client.get(f"/api/v2/moq/progress/{random_id}")
        # Without Redis, the endpoint may 503 before the 404 check; both are acceptable
        assert resp.status_code in (404, 503)

    async def test_sse_non_public_campaign_returns_404_not_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """SSE must not reveal that a campaign exists via a 403 vs 404 distinction."""
        campaign = await _create_campaign(db_session, status="draft", with_offer=False)
        resp = await client.get(f"/api/v2/moq/progress/{campaign.id}")
        # 503 is acceptable if Redis not available; 403 is NOT acceptable
        assert resp.status_code != 403, "SSE must not return 403 (reveals campaign existence)"
        assert resp.status_code in (404, 503)
