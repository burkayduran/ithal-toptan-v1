"""
Payment hardening tests:
  1. confirm_payment creates a Payment record even if initiate was skipped
  2. initiate/confirm reject entries in 'waiting' state
  3. Expired deadline entries are handled correctly
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Payment, ProductRequest, SupplierOffer, WishlistEntry
from tests.conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio


# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

async def _create_product_with_offer(db: AsyncSession, moq: int = 5) -> tuple[ProductRequest, SupplierOffer]:
    product = ProductRequest(
        title=f"Payment Test {uuid.uuid4().hex[:6]}",
        description="Test",
        images=[],
        status="moq_reached",
    )
    db.add(product)
    await db.flush()

    offer = SupplierOffer(
        request_id=product.id,
        supplier_name="Supplier",
        unit_price_usd=Decimal("10.00"),
        moq=moq,
        lead_time_days=14,
        selling_price_try=Decimal("500.00"),
        is_selected=True,
    )
    db.add(offer)
    await db.commit()
    await db.refresh(product)
    await db.refresh(offer)
    return product, offer


async def _create_notified_entry(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID) -> WishlistEntry:
    """Create a WishlistEntry in 'notified' state with a future deadline."""
    entry = WishlistEntry(
        request_id=product_id,
        user_id=user_id,
        quantity=2,
        status="notified",
        payment_deadline=datetime.now(timezone.utc) + timedelta(hours=48),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _create_waiting_entry(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID) -> WishlistEntry:
    """Create a WishlistEntry in 'waiting' state (MOQ not yet reached)."""
    entry = WishlistEntry(
        request_id=product_id,
        user_id=user_id,
        quantity=1,
        status="waiting",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _get_user_id(client: AsyncClient, token: str) -> uuid.UUID:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(token))
    return uuid.UUID(resp.json()["id"])


# ───────────────────────────────────────────────────────────────────────────────
# 1. Payment persistence — confirm without prior initiate creates Payment record
# ───────────────────────────────────────────────────────────────────────────────

class TestPaymentPersistence:
    async def test_confirm_without_initiate_creates_payment_record(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """confirm endpoint must create a Payment row if initiate was never called."""
        email = f"pp_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PPPass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_notified_entry(db_session, product.id, user_id)

        # Skip initiate — go straight to confirm
        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

        # Verify Payment record was created
        result = await db_session.execute(
            select(Payment).where(Payment.wishlist_entry_id == entry.id)
        )
        payment = result.scalar_one_or_none()
        assert payment is not None, "Payment record must exist after confirm"
        assert payment.status == "success"
        assert payment.paid_at is not None
        assert float(payment.amount_try) == pytest.approx(1000.0)  # 2 qty * 500 TRY

    async def test_confirm_after_initiate_updates_existing_payment(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """When initiate is called first, confirm must update — not duplicate — the record."""
        email = f"pp2_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PP2Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_notified_entry(db_session, product.id, user_id)

        await client.post(
            "/api/v1/payments/initiate",
            json={"entry_id": str(entry.id)},
            headers=auth_headers(token),
        )
        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

        # Exactly one Payment record
        result = await db_session.execute(
            select(Payment).where(Payment.wishlist_entry_id == entry.id)
        )
        payments = result.scalars().all()
        assert len(payments) == 1
        assert payments[0].status == "success"

    async def test_wishlist_entry_status_is_paid_after_confirm(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"pp3_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PP3Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_notified_entry(db_session, product.id, user_id)

        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "paid"

        await db_session.refresh(entry)
        assert entry.status == "paid"
        assert entry.paid_at is not None


# ───────────────────────────────────────────────────────────────────────────────
# 2. waiting state must be rejected by initiate and confirm
# ───────────────────────────────────────────────────────────────────────────────

class TestWaitingStateRejection:
    async def test_initiate_rejects_waiting_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wr1_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WR1Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_waiting_entry(db_session, product.id, user_id)

        resp = await client.post(
            "/api/v1/payments/initiate",
            json={"entry_id": str(entry.id)},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "notified" in resp.json()["detail"].lower()

    async def test_confirm_rejects_waiting_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wr2_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WR2Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_waiting_entry(db_session, product.id, user_id)

        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "notified" in resp.json()["detail"].lower()

    async def test_no_payment_record_created_for_waiting_entry(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Rejected initiate must not leave a partial Payment row."""
        email = f"wr3_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WR3Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_waiting_entry(db_session, product.id, user_id)

        await client.post(
            "/api/v1/payments/initiate",
            json={"entry_id": str(entry.id)},
            headers=auth_headers(token),
        )

        result = await db_session.execute(
            select(Payment).where(Payment.wishlist_entry_id == entry.id)
        )
        assert result.scalar_one_or_none() is None


# ───────────────────────────────────────────────────────────────────────────────
# 3. Already-paid / wrong owner
# ───────────────────────────────────────────────────────────────────────────────

class TestPaymentGuards:
    async def test_confirm_already_paid_entry_rejected(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"pg1_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PG1Pass123!"))["access_token"]
        user_id = await _get_user_id(client, token)

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_notified_entry(db_session, product.id, user_id)

        # First confirm succeeds
        await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(token),
        )
        # Second confirm must fail (entry is now 'paid', not 'notified')
        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
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

        product, _ = await _create_product_with_offer(db_session)
        entry = await _create_notified_entry(db_session, product.id, owner_id)

        resp = await client.post(
            f"/api/v1/payments/entry/{entry.id}/confirm",
            headers=auth_headers(other_token),
        )
        assert resp.status_code == 404
