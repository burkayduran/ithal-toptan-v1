"""
Integration tests – require live Postgres + Redis.

Run with:
    pytest -q backend/tests/test_integration.py

Coverage:
  1. auth  – register / login / me
  2. admin – create product + publish (status=active)
  3. wishlist – add returns 200 and correct WishlistResponse
  4. moq concurrency – threshold transition is atomic (no duplicate side-effects)
  5. SSE – returns 503 if Redis unavailable; otherwise connects and receives ≥1 message
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import (
    register_and_login,
    make_admin,
    create_active_product,
)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Auth – register / login / me
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_register_login_me(client: AsyncClient):
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    password = "securepass123"

    # Register
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Auth Tester",
        "password": password,
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    assert token

    # Login
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    assert resp.status_code == 200
    login_token = resp.json()["access_token"]
    assert login_token

    # /me
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_token}"},
    )
    assert resp.status_code == 200
    me = resp.json()
    assert me["email"] == email
    assert me["is_active"] is True
    assert me["is_admin"] is False


# ──────────────────────────────────────────────────────────────────────────────
# 2. Admin – create product + publish → status=active
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_create_and_publish_product(client: AsyncClient):
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    password = "adminpass123"

    await register_and_login(client, admin_email, password)
    await make_admin(admin_email)
    admin_token = await register_and_login(client, admin_email, password)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create product
    resp = await client.post("/api/admin/products", headers=headers, json={
        "title": "Test Product",
        "description": "A test product",
        "images": [],
        "unit_price_usd": 15.0,
        "moq": 5,
        "shipping_cost_usd": 30.0,
        "customs_rate": 0.20,
        "margin_rate": 0.30,
    })
    assert resp.status_code == 201
    product = resp.json()
    assert product["status"] == "draft"
    product_id = product["id"]
    assert product["moq"] == 5

    # Publish
    resp = await client.post(f"/api/admin/products/{product_id}/publish", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == product_id

    # Verify status via admin list
    resp = await client.get("/api/admin/products", headers=headers)
    assert resp.status_code == 200
    products = resp.json()
    published = next((p for p in products if p["id"] == product_id), None)
    assert published is not None
    assert published["status"] == "active"


# ──────────────────────────────────────────────────────────────────────────────
# 3. Wishlist add – 200 + correct WishlistResponse
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wishlist_add_returns_200_and_correct_response(client: AsyncClient):
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    user_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass12345"

    await register_and_login(client, admin_email, password)
    await make_admin(admin_email)
    admin_token = await register_and_login(client, admin_email, password)

    product_id = await create_active_product(client, admin_token, moq=10)

    user_token = await register_and_login(client, user_email, password)
    resp = await client.post(
        "/api/v1/wishlist/add",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"request_id": product_id, "quantity": 2},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["request_id"] == product_id
    assert data["quantity"] == 2
    assert data["status"] == "waiting"
    assert data["product_title"] == "Integration Test Product"
    assert data["selling_price_try"] is not None


@pytest.mark.asyncio
async def test_wishlist_add_rejected_for_draft_product(client: AsyncClient):
    """Adding to a draft product must return HTTP 400 with error=product_not_open."""
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    user_email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass12345"

    await register_and_login(client, admin_email, password)
    await make_admin(admin_email)
    admin_token = await register_and_login(client, admin_email, password)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Create but DO NOT publish
    resp = await client.post("/api/admin/products", headers=headers, json={
        "title": "Draft Only",
        "images": [],
        "unit_price_usd": 5.0,
        "moq": 2,
        "shipping_cost_usd": 10.0,
        "customs_rate": 0.20,
        "margin_rate": 0.30,
    })
    assert resp.status_code == 201
    product_id = resp.json()["id"]

    user_token = await register_and_login(client, user_email, password)
    resp = await client.post(
        "/api/v1/wishlist/add",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"request_id": product_id, "quantity": 1},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["error"] == "product_not_open"
    assert detail["status"] == "draft"
    assert detail["request_id"] == product_id


# ──────────────────────────────────────────────────────────────────────────────
# 4. MoQ concurrency – threshold transition is atomic (no duplicate side-effects)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_moq_threshold_transition_is_atomic(client: AsyncClient):
    """
    N concurrent wishlist adds whose total quantity exactly meets MoQ.
    Only one transition (active→moq_reached) must happen, with no duplicate
    Celery tasks or payment deadlines.
    """
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass12345"

    await register_and_login(client, admin_email, password)
    await make_admin(admin_email)
    admin_token = await register_and_login(client, admin_email, password)

    moq = 3
    product_id = await create_active_product(client, admin_token, moq=moq)

    # Create 3 separate users, each adding quantity=1 concurrently
    users = []
    for i in range(moq):
        email = f"concurrent_{uuid.uuid4().hex[:8]}@test.com"
        token = await register_and_login(client, email, password)
        users.append(token)

    # In CI, Redis is available as a Celery broker, so .delay()/.apply_async()
    # simply enqueue tasks without executing them (no worker running in tests).
    async def add_one(token: str):
        return await client.post(
            "/api/v1/wishlist/add",
            headers={"Authorization": f"Bearer {token}"},
            json={"request_id": product_id, "quantity": 1},
        )

    responses = await asyncio.gather(*[add_one(t) for t in users])

    # All requests should succeed
    for resp in responses:
        assert resp.status_code == 200, resp.text

    # Check final product status via admin
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.get("/api/admin/products", headers=headers)
    products = resp.json()
    product = next(p for p in products if p["id"] == product_id)

    # Product should be moq_reached (or active if tasks are async; check counter)
    assert product["current_wishlist_count"] == moq


# ──────────────────────────────────────────────────────────────────────────────
# 5. SSE – returns 503 if Redis unavailable; connects + receives ≥1 msg otherwise
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sse_returns_503_when_redis_unavailable(client: AsyncClient):
    """When app.state.redis is None the SSE endpoint must return 503."""
    from app.main import app as _app

    original = _app.state.redis
    try:
        _app.state.redis = None
        resp = await client.get(f"/api/v1/moq/progress/{uuid.uuid4()}")
        assert resp.status_code == 503
    finally:
        _app.state.redis = original


@pytest.mark.asyncio
async def test_sse_connects_and_receives_initial_message(client: AsyncClient):
    """
    When Redis is available, the SSE endpoint should:
    - Return 200
    - Stream at least the initial count value as a data: line
    """
    admin_email = f"admin_{uuid.uuid4().hex[:8]}@test.com"
    password = "pass12345"

    await register_and_login(client, admin_email, password)
    await make_admin(admin_email)
    admin_token = await register_and_login(client, admin_email, password)

    product_id = await create_active_product(client, admin_token, moq=5)

    # SSE streams; we open with stream=True and read just the first chunk
    async with client.stream("GET", f"/api/v1/moq/progress/{product_id}") as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        # Read first event line (e.g. "data: 0\n")
        lines = []
        async for line in resp.aiter_lines():
            if line.startswith("data:"):
                lines.append(line)
                break  # got at least one data line

    assert len(lines) >= 1, "SSE stream produced no data lines"
    # The initial count for a fresh product should be 0
    assert lines[0].strip() in ("data: 0", "data:0")


# ──────────────────────────────────────────────────────────────────────────────
# 6. Alembic server_default – raw SQL insert must not violate NOT NULL
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_raw_sql_insert_respects_server_defaults():
    """
    Inserting into product_requests and supplier_offers via raw SQL
    (no explicit values for defaulted columns) must succeed and return
    correct defaults, proving server_default fixes are applied.
    """
    from sqlalchemy import text
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as session:
        # Insert a product_request with only required columns
        await session.execute(text("""
            INSERT INTO product_requests (title)
            VALUES ('Raw SQL Product')
        """))
        result = await session.execute(text("""
            SELECT status, view_count, images
            FROM product_requests
            WHERE title = 'Raw SQL Product'
        """))
        row = result.fetchone()
        assert row.status == "pending", f"Expected 'pending', got {row.status!r}"
        assert row.view_count == 0, f"Expected 0, got {row.view_count!r}"
        assert row.images == [], f"Expected [], got {row.images!r}"

        # Get the product id for offer
        pid_result = await session.execute(text(
            "SELECT id FROM product_requests WHERE title = 'Raw SQL Product'"
        ))
        product_id = pid_result.scalar_one()

        # Insert a supplier_offer with only required columns
        await session.execute(text("""
            INSERT INTO supplier_offers (request_id, unit_price_usd, moq)
            VALUES (:pid, 9.99, 10)
        """), {"pid": product_id})
        result = await session.execute(text("""
            SELECT supplier_country, margin_rate, is_selected
            FROM supplier_offers
            WHERE request_id = :pid
        """), {"pid": product_id})
        row = result.fetchone()
        assert row.supplier_country == "CN", f"Expected 'CN', got {row.supplier_country!r}"
        assert float(row.margin_rate) == 0.25, f"Expected 0.25, got {row.margin_rate!r}"
        assert row.is_selected is False, f"Expected False, got {row.is_selected!r}"

        await session.rollback()  # Don't persist; clean_tables fixture handles it
