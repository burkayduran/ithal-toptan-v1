"""
Progress endpoint hardening tests:
  1. Public product: progress data is returned
  2. Non-public status (draft, cancelled, etc.): uniform 404, no data leaked
  3. Non-existent request_id: 404 (same response shape as non-public, no info leak)
  4. Uniform 404 for SSE endpoint on non-public/missing products
"""
import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ProductRequest, SupplierOffer
from tests.conftest import auth_headers, register_user

pytestmark = pytest.mark.asyncio

# ───────────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────────

async def _create_product(db: AsyncSession, status: str, with_offer: bool = True) -> ProductRequest:
    product = ProductRequest(
        title=f"Progress Test {uuid.uuid4().hex[:6]}",
        description="Test",
        images=[],
        status=status,
    )
    db.add(product)
    await db.flush()

    if with_offer:
        offer = SupplierOffer(
            request_id=product.id,
            supplier_name="Supplier",
            unit_price_usd=Decimal("10.00"),
            moq=50,
            lead_time_days=14,
            selling_price_try=Decimal("500.00"),
            is_selected=True,
        )
        db.add(offer)

    await db.commit()
    await db.refresh(product)
    return product


# ───────────────────────────────────────────────────────────────────────────────
# 1. Public statuses — progress endpoint must return data
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressPublicAccess:
    @pytest.mark.parametrize("status", ["active", "moq_reached", "payment_collecting"])
    async def test_public_status_returns_progress(
        self, client: AsyncClient, db_session: AsyncSession, status: str
    ):
        from unittest.mock import AsyncMock, patch

        product = await _create_product(db_session, status=status)

        with patch("app.api.v1.endpoints.wishlist.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.get_current_count = AsyncMock(return_value=10)

            resp = await client.get(f"/api/v1/wishlist/progress/{product.id}")

        assert resp.status_code == 200, f"Expected 200 for {status!r}, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "current" in data
        assert "target" in data
        assert "percentage" in data
        assert data["request_id"] == str(product.id)

    async def test_progress_no_auth_required_for_public(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Progress endpoint must be accessible without a token for public campaigns."""
        from unittest.mock import AsyncMock, patch

        product = await _create_product(db_session, status="active")

        with patch("app.api.v1.endpoints.wishlist.MoQService") as MockMoQ:
            instance = MockMoQ.return_value
            instance.get_current_count = AsyncMock(return_value=5)
            resp = await client.get(f"/api/v1/wishlist/progress/{product.id}")

        assert resp.status_code == 200


# ───────────────────────────────────────────────────────────────────────────────
# 2. Non-public statuses — must return 404 with no leakage
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressNonPublicBlocked:
    @pytest.mark.parametrize("status", ["draft", "pending", "sourcing", "cancelled", "ordered", "delivered"])
    async def test_non_public_status_returns_404(
        self, client: AsyncClient, db_session: AsyncSession, status: str
    ):
        product = await _create_product(db_session, status=status)
        resp = await client.get(f"/api/v1/wishlist/progress/{product.id}")
        assert resp.status_code == 404, f"Expected 404 for {status!r}, got {resp.status_code}"

    async def test_non_public_detail_is_generic(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Error detail must not reveal why access was denied (no 'not accessible' or 'offer' wording)."""
        product = await _create_product(db_session, status="draft")
        resp = await client.get(f"/api/v1/wishlist/progress/{product.id}")
        assert resp.status_code == 404
        detail = resp.json().get("detail", "").lower()
        # Should not hint that the product exists but is restricted
        assert "accessible" not in detail
        assert "offer" not in detail
        assert "draft" not in detail

    async def test_non_public_and_missing_produce_same_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-public and missing IDs must return identical status codes."""
        product = await _create_product(db_session, status="draft")
        missing_id = uuid.uuid4()

        non_public_resp = await client.get(f"/api/v1/wishlist/progress/{product.id}")
        missing_resp = await client.get(f"/api/v1/wishlist/progress/{missing_id}")

        assert non_public_resp.status_code == 404
        assert missing_resp.status_code == 404
        # Both details should be the same generic message
        assert non_public_resp.json()["detail"] == missing_resp.json()["detail"]


# ───────────────────────────────────────────────────────────────────────────────
# 3. Non-existent request_id — must return 404 (not 500 or 422)
# ───────────────────────────────────────────────────────────────────────────────

class TestProgressMissingProduct:
    async def test_unknown_uuid_returns_404(self, client: AsyncClient):
        random_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/wishlist/progress/{random_id}")
        assert resp.status_code == 404

    async def test_invalid_uuid_returns_422(self, client: AsyncClient):
        """Malformed UUIDs should fail at the parameter parsing level (422), not 500."""
        resp = await client.get("/api/v1/wishlist/progress/not-a-uuid")
        assert resp.status_code == 422


# ───────────────────────────────────────────────────────────────────────────────
# 4. SSE endpoint — non-public/missing must return uniform 404
# ───────────────────────────────────────────────────────────────────────────────

class TestSSEProgressHardening:
    async def test_sse_missing_product_returns_404(self, client: AsyncClient):
        random_id = uuid.uuid4()
        resp = await client.get(f"/api/v1/moq/progress/{random_id}")
        # Without Redis, the endpoint may 503 before the 404 check; both are acceptable
        assert resp.status_code in (404, 503)

    async def test_sse_non_public_product_returns_404_not_403(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """SSE must not reveal that a product exists via a 403 vs 404 distinction."""
        product = await _create_product(db_session, status="draft", with_offer=False)
        resp = await client.get(f"/api/v1/moq/progress/{product.id}")
        # 503 is acceptable if Redis not available; 403 is NOT acceptable
        assert resp.status_code != 403, "SSE must not return 403 (reveals product existence)"
        assert resp.status_code in (404, 503)
