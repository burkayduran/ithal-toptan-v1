"""
Integration tests for:
  1. Register → login → /me flow
  2. Authenticated GET /wishlist/my
  3. Wishlist add rollback safety (IntegrityError → 409, no side effects)
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
    Category,
    ProductRequest,
    SupplierOffer,
    WishlistEntry,
)
from app.services.moq_service import MoQService

from tests.conftest import auth_headers, login_user, register_user

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

async def _create_product(
    db: AsyncSession,
    status: str = "active",
    moq: int = 10,
) -> tuple[ProductRequest, SupplierOffer]:
    """Create a ProductRequest + selected SupplierOffer in the test DB."""
    product = ProductRequest(
        title=f"Test Product {uuid.uuid4().hex[:6]}",
        description="Integration test product",
        images=[],
        status=status,
    )
    db.add(product)
    await db.flush()  # get product.id

    offer = SupplierOffer(
        request_id=product.id,
        supplier_name="Test Supplier",
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
# 2. Authenticated GET /wishlist/my
# ═══════════════════════════════════════════════════════════════════════════════

class TestWishlistMy:
    async def test_wishlist_my_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/wishlist/my")
        assert resp.status_code == 401

    async def test_wishlist_my_empty_for_new_user(self, client: AsyncClient):
        email = f"wl_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WLPass123!"))["access_token"]

        resp = await client.get("/api/v1/wishlist/my", headers=auth_headers(token))
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_wishlist_my_shows_joined_products(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        email = f"wljoin_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "WLJoin1!"))["access_token"]

        product, _ = await _create_product(db_session, status="active", moq=5)

        with patch("app.api.v1.endpoints.wishlist.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.sync_counter_from_db = AsyncMock(return_value=1)
            instance.check_and_trigger = AsyncMock(return_value={
                "threshold_met": False, "transition_performed": False, "status_after": "active"
            })

            add_resp = await client.post(
                "/api/v1/wishlist/add",
                json={"request_id": str(product.id), "quantity": 2},
                headers=auth_headers(token),
            )
        assert add_resp.status_code == 200

        my_resp = await client.get("/api/v1/wishlist/my", headers=auth_headers(token))
        assert my_resp.status_code == 200
        items = my_resp.json()
        assert len(items) == 1
        assert items[0]["request_id"] == str(product.id)
        assert items[0]["quantity"] == 2
        assert items[0]["status"] == "waiting"
        assert items[0]["product_title"] == product.title


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Rollback safety — IntegrityError → 409, no side effects fired
# ═══════════════════════════════════════════════════════════════════════════════

class TestWishlistRollbackSafety:
    async def test_integrity_error_returns_409_no_side_effects(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        When the DB raises IntegrityError during the upsert, the endpoint must:
          - return HTTP 409 (not 200 or 500)
          - NOT call sync_counter_from_db or check_and_trigger
        """
        email = f"rb_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "RBPass123!"))["access_token"]
        product, _ = await _create_product(db_session, status="active", moq=5)

        from sqlalchemy.exc import IntegrityError as SAIntegrityError

        sync_mock = AsyncMock()
        trigger_mock = AsyncMock()

        with patch("app.api.v1.endpoints.wishlist.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.sync_counter_from_db = sync_mock
            instance.check_and_trigger = trigger_mock

            # Patch db.execute to raise IntegrityError on the upsert
            original_execute = db_session.execute

            call_count = {"n": 0}

            async def patched_execute(stmt, *args, **kwargs):
                # First SELECT (product fetch) and second SELECT (existing entry) pass through.
                # The third call is the upsert INSERT — raise IntegrityError on it.
                call_count["n"] += 1
                if call_count["n"] == 3:
                    raise SAIntegrityError("mock", {}, Exception("unique violation"))
                return await original_execute(stmt, *args, **kwargs)

            with patch.object(db_session, "execute", side_effect=patched_execute):
                resp = await client.post(
                    "/api/v1/wishlist/add",
                    json={"request_id": str(product.id), "quantity": 1},
                    headers=auth_headers(token),
                )

        assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text}"
        sync_mock.assert_not_called()
        trigger_mock.assert_not_called()

    async def test_successful_add_runs_side_effects(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Successful commit must call sync_counter_from_db and check_and_trigger."""
        email = f"se_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "SEPass123!"))["access_token"]
        product, _ = await _create_product(db_session, status="active", moq=100)

        sync_mock = AsyncMock(return_value=1)
        trigger_mock = AsyncMock(return_value={
            "threshold_met": False, "transition_performed": False, "status_after": "active"
        })

        with patch("app.api.v1.endpoints.wishlist.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.sync_counter_from_db = sync_mock
            instance.check_and_trigger = trigger_mock

            resp = await client.post(
                "/api/v1/wishlist/add",
                json={"request_id": str(product.id), "quantity": 1},
                headers=auth_headers(token),
            )

        assert resp.status_code == 200
        sync_mock.assert_called_once()
        trigger_mock.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. payment_collecting state machine transition
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
        process_expired_entries must transition product from moq_reached → payment_collecting
        before marking notified entries as expired.
        """
        product, offer = await _create_product(db_session, status="moq_reached", moq=2)

        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.execute(
            update(ProductRequest)
            .where(ProductRequest.id == product.id)
            .values(moq_reached_at=past_deadline - timedelta(hours=48), payment_deadline=past_deadline)
        )

        # Add a notified entry past its deadline
        entry = WishlistEntry(
            request_id=product.id,
            user_id=uuid.uuid4(),  # phantom user id for test
            quantity=1,
            status="notified",
            notified_at=past_deadline - timedelta(hours=48),
            payment_deadline=past_deadline,
        )
        db_session.add(entry)
        await db_session.commit()

        moq_svc = await self._make_moq_service(db_session)
        await moq_svc.process_expired_entries(product.id)

        refreshed = await db_session.execute(
            select(ProductRequest).where(ProductRequest.id == product.id)
        )
        updated_product = refreshed.scalar_one()

        # With 0 paid entries (< moq=2), it should reset to active after payment_collecting
        assert updated_product.status == "active", (
            f"Expected 'active' after reset, got '{updated_product.status}'"
        )

    async def test_trigger_payment_phase_sets_moq_reached(self, db_session: AsyncSession):
        """trigger_payment_phase must transition active → moq_reached."""
        product, offer = await _create_product(db_session, status="active", moq=2)

        moq_svc = await self._make_moq_service(db_session)

        with patch("app.tasks.email_tasks.send_moq_reached_email") as mock_email, \
             patch("app.tasks.moq_tasks.cleanup_expired_entries") as mock_cleanup:
            mock_email.delay = MagicMock()
            mock_cleanup.apply_async = MagicMock()
            result = await moq_svc.trigger_payment_phase(product.id, offer)

        assert result is True

        refreshed = await db_session.execute(
            select(ProductRequest).where(ProductRequest.id == product.id)
        )
        updated = refreshed.scalar_one()
        assert updated.status == "moq_reached"
        assert updated.payment_deadline is not None

    async def test_payment_collecting_to_ordered_when_enough_paid(self, db_session: AsyncSession):
        """
        When paid_count >= moq after the deadline, product must go
        payment_collecting → ordered (not skip payment_collecting).
        """
        product, offer = await _create_product(db_session, status="moq_reached", moq=1)

        past_deadline = datetime.now(timezone.utc) - timedelta(hours=1)
        await db_session.execute(
            update(ProductRequest)
            .where(ProductRequest.id == product.id)
            .values(moq_reached_at=past_deadline - timedelta(hours=48), payment_deadline=past_deadline)
        )

        # Add a PAID entry — this satisfies the moq
        paid_entry = WishlistEntry(
            request_id=product.id,
            user_id=uuid.uuid4(),
            quantity=1,
            status="paid",
        )
        db_session.add(paid_entry)
        await db_session.commit()

        moq_svc = await self._make_moq_service(db_session)
        await moq_svc.process_expired_entries(product.id)

        refreshed = await db_session.execute(
            select(ProductRequest).where(ProductRequest.id == product.id)
        )
        updated = refreshed.scalar_one()
        assert updated.status == "ordered", (
            f"Expected 'ordered' when paid_count >= moq, got '{updated.status}'"
        )

    async def test_join_rejected_when_payment_collecting(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Wishlist add must be rejected when product is in payment_collecting state."""
        email = f"pc_{uuid.uuid4().hex[:8]}@test.com"
        token = (await register_user(client, email, "PCPass123!"))["access_token"]
        product, _ = await _create_product(db_session, status="payment_collecting", moq=5)

        resp = await client.post(
            "/api/v1/wishlist/add",
            json={"request_id": str(product.id), "quantity": 1},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "not accepting" in resp.json()["detail"].lower()
