"""
Hardening tests:
  1. Auth register/login happy paths and error cases
  2. calculate-price endpoint with valid and invalid inputs
  3. Status enum validation on ProductUpdate and ProductRequestUpdate schemas
"""
import pytest
from pydantic import ValidationError

from tests.conftest import register_user, auth_headers

pytestmark = pytest.mark.asyncio


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Auth endpoints
# ═══════════════════════════════════════════════════════════════════════════════

async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json={
        "email": "hardening_reg@example.com",
        "password": "password123",
        "full_name": "Hardening User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client):
    payload = {"email": "dup_hardening@example.com", "password": "pw123"}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"].lower()


async def test_login_success(client):
    email, pw = "login_hardening@example.com", "pw123456"
    await register_user(client, email, pw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


async def test_login_wrong_password(client):
    email, pw = "login_wrong@example.com", "correctpw"
    await register_user(client, email, pw)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpw"})
    assert resp.status_code == 401


async def test_login_unknown_email(client):
    resp = await client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "whatever",
    })
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 2. calculate-price endpoint
# ═══════════════════════════════════════════════════════════════════════════════

async def _admin_token(client) -> str:
    """Register a user and promote to admin directly via DB, return token."""
    from app.models.models import User
    from sqlalchemy import select, update
    from app.db.session import get_db

    resp = await client.post("/api/v1/auth/register", json={
        "email": "calc_admin@example.com",
        "password": "adminpw123",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    # Promote to admin by patching the DB through the app dependency
    async for db in get_db():
        result = await db.execute(
            select(User).where(User.email == "calc_admin@example.com")
        )
        user = result.scalar_one()
        user.is_admin = True
        await db.commit()
        break

    return token


async def test_calculate_price_valid(client):
    token = await _admin_token(client)
    resp = await client.post(
        "/api/v2/admin/calculate-price",
        json={
            "unit_price_usd": 10.0,
            "moq": 100,
            "shipping_cost_usd": 1.0,
            "customs_rate": 0.35,
            "margin_rate": 0.30,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "selling_price_try" in data
    assert float(data["selling_price_try"]) > 0


async def test_calculate_price_missing_fields(client):
    token = await _admin_token(client)
    # Missing required unit_price_usd and moq
    resp = await client.post(
        "/api/v2/admin/calculate-price",
        json={"shipping_cost_usd": 1.0},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


async def test_calculate_price_invalid_values(client):
    token = await _admin_token(client)
    # unit_price_usd must be > 0
    resp = await client.post(
        "/api/v2/admin/calculate-price",
        json={"unit_price_usd": -5.0, "moq": 10},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


async def test_calculate_price_requires_admin(client):
    resp = await client.post("/api/v2/admin/calculate-price", json={
        "unit_price_usd": 10.0,
        "moq": 100,
    })
    assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Status enum validation (schema-level, no HTTP needed)
# ═══════════════════════════════════════════════════════════════════════════════

def test_product_update_valid_status():
    from app.schemas.schemas import ProductUpdate
    obj = ProductUpdate(status="active")
    assert obj.status == "active"


def test_product_update_invalid_status():
    from app.schemas.schemas import ProductUpdate
    with pytest.raises(ValidationError):
        ProductUpdate(status="nonexistent_status")


def test_product_update_none_status_allowed():
    from app.schemas.schemas import ProductUpdate
    obj = ProductUpdate(status=None)
    assert obj.status is None


def test_product_request_update_valid_status():
    from app.schemas.schemas import ProductRequestUpdate
    obj = ProductRequestUpdate(status="approved")
    assert obj.status == "approved"


def test_product_request_update_invalid_status():
    from app.schemas.schemas import ProductRequestUpdate
    with pytest.raises(ValidationError):
        ProductRequestUpdate(status="active")  # not a valid RequestStatus


def test_price_calculate_request_valid():
    from app.schemas.schemas import PriceCalculateRequest
    obj = PriceCalculateRequest(unit_price_usd=5.0, moq=50)
    assert obj.unit_price_usd == 5.0
    assert obj.moq == 50
    # No request_id field
    assert not hasattr(obj, "request_id")


def test_price_calculate_request_invalid_price():
    from app.schemas.schemas import PriceCalculateRequest
    with pytest.raises(ValidationError):
        PriceCalculateRequest(unit_price_usd=0.0, moq=10)  # must be > 0


def test_price_calculate_request_invalid_moq():
    from app.schemas.schemas import PriceCalculateRequest
    with pytest.raises(ValidationError):
        PriceCalculateRequest(unit_price_usd=5.0, moq=0)  # must be >= 1
