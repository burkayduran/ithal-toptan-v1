"""
Pytest fixtures for integration tests.

Requires:
  - DATABASE_URL  pointing to a real (test) PostgreSQL DB
  - REDIS_URL     pointing to a real (test) Redis
  - SECRET_KEY    any string

These are set in the environment or via .env.test.
The GitHub Actions workflow provides Postgres + Redis service containers.
"""
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# ── Force test settings before importing app ──────────────────────────────────
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-integration-tests")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_ithal")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("EMAIL_PROVIDER", "fake")
os.environ.setdefault("MOQ_SYNC_STRATEGY", "strict")

from app.main import app  # noqa: E402  – import after env setup
from app.db.session import Base  # noqa: E402
from app.core.config import settings  # noqa: E402


# ── Test DB engine ─────────────────────────────────────────────────────────────
test_engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


# ── Session-scoped Redis pool for the app under test ─────────────────────────
# httpx's ASGITransport only sends type="http" scopes; it never fires the
# ASGI lifespan events, so FastAPI's lifespan context manager (which calls
# create_redis_pool() and stores the result in app.state.redis) never runs.
# We replicate that startup step here so get_redis() works during tests.
@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_app_redis():
    from app.core.redis import create_redis_pool
    app.state.redis = create_redis_pool()
    await app.state.redis.ping()   # fail fast if Redis is unreachable
    yield
    await app.state.redis.aclose()
    app.state.redis = None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables(init_app_redis):
    """Create all tables once at session start and drop them at the end."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Truncate all tables (except schema) between tests for isolation."""
    yield
    async with test_engine.begin() as conn:
        # Truncate in reverse-dependency order
        await conn.execute(
            __import__("sqlalchemy", fromlist=["text"]).text(
                "TRUNCATE TABLE notifications, batch_orders, payments, "
                "wishlist_entries, supplier_offers, product_requests, "
                "categories, users RESTART IDENTITY CASCADE"
            )
        )


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Return an httpx AsyncClient wired to the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Helpers ───────────────────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, email: str, password: str) -> str:
    """Register (idempotent) and return a Bearer token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Test User",
        "password": password,
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


async def make_admin(email: str) -> None:
    """Promote a user to is_admin=True via direct DB update."""
    from sqlalchemy import text
    async with TestSessionLocal() as session:
        await session.execute(
            text("UPDATE users SET is_admin = true WHERE email = :email"),
            {"email": email},
        )
        await session.commit()


async def create_active_product(client: AsyncClient, admin_token: str, moq: int = 3) -> str:
    """Create a product via admin API and publish it; return product_id."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await client.post("/api/admin/products", headers=headers, json={
        "title": "Integration Test Product",
        "description": "pytest fixture",
        "images": [],
        "unit_price_usd": 10.0,
        "moq": moq,
        "shipping_cost_usd": 20.0,
        "customs_rate": 0.20,
        "margin_rate": 0.30,
    })
    resp.raise_for_status()
    product_id = resp.json()["id"]

    pub = await client.post(f"/api/admin/products/{product_id}/publish", headers=headers)
    pub.raise_for_status()
    return product_id
