"""
Test configuration and fixtures.

Requires a test PostgreSQL database. Set TEST_DATABASE_URL in environment or .env.test file.
Falls back to modifying the default DATABASE_URL to use a "test_" prefixed database.

Install test dependencies:
    pip install pytest pytest-asyncio httpx
"""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Determine test DB URL — use TEST_DATABASE_URL if set, otherwise derive from DATABASE_URL
_default_db = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/ithal_toptan")
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    _default_db.replace("/ithal_toptan", "/ithal_toptan_test")
    .replace("postgresql://", "postgresql+asyncpg://")
    .replace("postgresql+asyncpg+asyncpg://", "postgresql+asyncpg://"),
)
if "asyncpg" not in TEST_DATABASE_URL:
    TEST_DATABASE_URL = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Patch settings before importing app modules
os.environ.setdefault("DATABASE_URL", _default_db)
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

from app.db.session import Base
from app.main import app
from app.db.session import get_db


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create async engine for test database. Creates all tables once per session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(test_engine):
    """
    Per-test DB session that wraps each test in a transaction that is
    rolled back on teardown — keeps tests isolated without recreating tables.
    """
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with test_engine.begin() as conn:
        async with AsyncSession(bind=conn) as session:
            yield session
            await conn.rollback()


@pytest_asyncio.fixture()
async def client(db_session):
    """HTTP test client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def register_user(client: AsyncClient, email: str, password: str, full_name: str = "Test User") -> dict:
    """Register a user and return the response JSON."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })
    assert resp.status_code == 201, resp.text
    return resp.json()


async def login_user(client: AsyncClient, email: str, password: str) -> str:
    """Login and return access token."""
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
