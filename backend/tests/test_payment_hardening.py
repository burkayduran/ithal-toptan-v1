"""
Payment hardening tests (V2):
  1. confirm_payment creates a PaymentTransaction record
  2. confirm rejects participants not in 'invited' state
  3. Expired deadline participants are handled correctly (BUG 1 guard)
  4. Already-paid / wrong owner
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import (
    Campaign, CampaignParticipant, PaymentTransaction,
    Product, SupplierOffer,
)
from tests.conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

async def _create_campaign_with_offer(db: AsyncSession, moq: int = 5) -> tuple[Campaign, Product, SupplierOffer]:
    product = Product(
        title=f"Payment Test {uuid.uuid4().hex[:6]}",
        description="Test",
        images=[],
    )
    db.add(product)
    await db.flush()

    campaign = Campaign(
        product_id=product.id,
        status="moq_reached",
        moq=moq,
        selling_price_try_snapshot=Decimal("500.00"),
        unit_price_usd_snapshot=Decimal("10.00"),
    )
    db.add(campaign)
    await db.flush()

    offer = SupplierOffer(
        campaign_id=campaign.id,
        supplier_name="Supplier",
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


async def _create_invited_participant(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID, quantity: int = 2,
) -> CampaignParticipant:
    """Create a CampaignParticipant in 'invited' state with a future deadline."""
    participant = CampaignParticipant(
        campaign_id=campaign_id,
        user_id=user_id,
        quantity=quantity,
        status="invited",
        invited_at=datetime.now(timezone.utc),
        payment_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return participant


async def _create_joined_participant(
    db: AsyncSession, campaign_id: uuid.UUID, user_id: uuid.UUID,
) -> CampaignParticipant:
    """Create a CampaignParticipant in 'joined' state (MOQ not yet reached)."""
    participant = CampaignParticipant(
        campaign_id=campaign_id,
        user_id=user_id,
        quantity=1,
        status="joined",
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return participant


async def _get_user_id(client: AsyncClient, token: str) -> uuid.UUID:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    return uuid.UUID(resp.json()["id"])


# ───────────────────────────────────────────────────────────────────────────────
# 1. Payment persistence — confirm creates PaymentTransaction record
# ───────────────────────────────────────────────────────────────────────────────

class TestPaymentPersistence:
    async def test_confirm_creates_payment_transaction(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"pp_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PPPass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_invited_participant(db_session, campaign.id, user_id)

        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

        # Verify PaymentTransaction record was created
        result = await db_session.execute(
            select(PaymentTransaction).where(PaymentTransaction.participant_id == participant.id)
        )
        tx = result.scalar_one_or_none()
        assert tx is not None, "PaymentTransaction must exist after confirm"
        assert tx.status == "success"
        assert tx.completed_at is not None
        assert float(tx.amount_try) == pytest.approx(1000.0)  # 2 qty * 500 TRY

    async def test_participant_status_is_paid_after_confirm(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"pp3_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PP3Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_invited_participant(db_session, campaign.id, user_id)

        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

        await db_session.refresh(participant)
        assert participant.status == "paid"
        assert participant.paid_at is not None


# ───────────────────────────────────────────────────────────────────────────────
# 2. joined state must be rejected by confirm
# ───────────────────────────────────────────────────────────────────────────────

class TestJoinedStateRejection:
    async def test_confirm_rejects_joined_participant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wr2_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WR2Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_joined_participant(db_session, campaign.id, user_id)

        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "invited" in resp.json()["detail"].lower()

    async def test_no_transaction_created_for_joined_participant(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wr3_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WR3Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_joined_participant(db_session, campaign.id, user_id)

        await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )

        result = await db_session.execute(
            select(PaymentTransaction).where(PaymentTransaction.participant_id == participant.id)
        )
        assert result.scalar_one_or_none() is None


# ───────────────────────────────────────────────────────────────────────────────
# 3. Deadline guard (BUG 1) — expired deadline must be rejected
# ───────────────────────────────────────────────────────────────────────────────

class TestDeadlineGuard:
    async def test_confirm_rejects_expired_deadline(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"dl_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "DLPass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_invited_participant(db_session, campaign.id, user_id)

        # Set deadline to past
        participant.payment_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.commit()

        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "süresi dolmuş" in resp.json()["detail"].lower() or "deadline" in resp.json()["detail"].lower()


# ───────────────────────────────────────────────────────────────────────────────
# 4. Already-paid / wrong owner
# ───────────────────────────────────────────────────────────────────────────────

class TestPaymentGuards:
    async def test_confirm_already_paid_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"pg1_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PG1Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_invited_participant(db_session, campaign.id, user_id)

        # First confirm succeeds
        await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        # Second confirm must fail (participant is now 'paid', not 'invited')
        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    async def test_another_user_cannot_confirm(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        owner_email = f"pg2a_{uuid.uuid4().hex[:8]}@test.com"
        owner_token = (await register_user(client, owner_email, "PG2APass!"))["access_token"]
        owner_id = await _get_user_id(client, owner_token)

        other_email = f"pg2b_{uuid.uuid4().hex[:8]}@test.com"
        other_token = (await register_user(client, other_email, "PG2BPass!"))["access_token"]

        campaign, _, _ = await _create_campaign_with_offer(db_session)
        participant = await _create_invited_participant(db_session, campaign.id, owner_id)

        resp = await client.post(
            f"/api/v2/payments/{participant.id}/confirm",
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 404
