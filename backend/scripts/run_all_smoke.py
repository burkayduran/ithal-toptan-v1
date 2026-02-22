#!/usr/bin/env python3
"""
Smoke & concurrency test runner.

Runs all checks end-to-end and exits with:
  0  – all tests passed
  1  – one or more tests failed

Tests:
  1. DB connectivity
  2. Redis connectivity
  3. Wishlist concurrency / duplicate-prevention (uq_wishlist_user_request)
  4. Redis TTL race
  5. MoQ atomic-counter race
  6. Email smoke test (fake provider)
  7. Notification unique-constraint enforcement (uq_notification_user_request_type)
"""
import asyncio
import os
import sys
import uuid

# Make sure app/ is importable when running from repo root or backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import redis.asyncio as aioredis
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.auth import get_password_hash
from app.db.session import AsyncSessionLocal, Base, engine
from app.models.models import (
    Notification,
    ProductRequest,
    SupplierOffer,
    User,
    WishlistEntry,
)
from app.services.moq_service import MoQService

PASS = "PASS"
FAIL = "FAIL"
_failures: list[str] = []


def _log(msg: str) -> None:
    print(msg, flush=True)


def _record_failure(test_name: str, reason: str) -> None:
    _failures.append(f"{test_name}: {reason}")
    _log(f"[{FAIL}] {test_name}: {reason}")


def _pass(test_name: str) -> None:
    _log(f"[{PASS}] {test_name}")


# ── 1. DB connectivity ────────────────────────────────────────────────────────

async def test_db_connectivity() -> None:
    name = "DB connectivity"
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(text("SELECT 1"))
            assert result.scalar() == 1
        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))


# ── 2. Redis connectivity ─────────────────────────────────────────────────────

async def test_redis_connectivity() -> None:
    name = "Redis connectivity"
    try:
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pong = await r.ping()
        assert pong is True
        await r.aclose()
        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))


# ── 3. Wishlist concurrency ───────────────────────────────────────────────────

async def test_wishlist_concurrency() -> None:
    name = "Wishlist concurrency (uq_wishlist_user_request)"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        # Create seed data
        async with AsyncSessionLocal() as db:
            user = User(
                email=f"smoke-concurrency-{uuid.uuid4()}@test.local",
                hashed_password=get_password_hash("testpass123"),
                is_active=True,
            )
            db.add(user)
            await db.flush()

            product = ProductRequest(
                title="Concurrency Smoke Test Product",
                status="active",
                created_by=user.id,
            )
            db.add(product)
            await db.flush()

            offer = SupplierOffer(
                request_id=product.id,
                unit_price_usd=10.00,
                moq=5,
                is_selected=True,
                selling_price_try=500.00,
            )
            db.add(offer)
            await db.commit()
            product_id = product.id
            user_id = user.id

        # 5 concurrent inserts for the same (user, product) pair
        async def _try_insert() -> bool:
            async with AsyncSessionLocal() as db:
                entry = WishlistEntry(
                    request_id=product_id,
                    user_id=user_id,
                    quantity=1,
                    status="waiting",
                )
                db.add(entry)
                try:
                    await db.commit()
                    return True
                except IntegrityError:
                    await db.rollback()
                    return False

        results = await asyncio.gather(*[_try_insert() for _ in range(5)])
        successes = sum(results)

        if successes != 1:
            _record_failure(name, f"Expected exactly 1 insert to succeed, got {successes}")
            return

        # Confirm DB has exactly 1 row
        async with AsyncSessionLocal() as db:
            rows = (
                await db.execute(
                    select(WishlistEntry).where(
                        WishlistEntry.request_id == product_id,
                        WishlistEntry.user_id == user_id,
                    )
                )
            ).scalars().all()
            if len(rows) != 1:
                _record_failure(name, f"Expected 1 DB row, found {len(rows)}")
                return

        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))
    finally:
        await r.aclose()


# ── 4. Redis TTL race ─────────────────────────────────────────────────────────

async def test_redis_ttl() -> None:
    name = "Redis TTL expiry"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        key = f"smoke:ttl:{uuid.uuid4()}"
        await r.set(key, "hello", ex=2)

        val = await r.get(key)
        assert val == "hello", f"Expected 'hello', got '{val}'"

        ttl = await r.ttl(key)
        assert 0 < ttl <= 2, f"Unexpected TTL={ttl}"

        await asyncio.sleep(3)
        expired = await r.get(key)
        assert expired is None, f"Key should have expired, got '{expired}'"

        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))
    finally:
        await r.aclose()


# ── 5. MoQ atomic-counter race ────────────────────────────────────────────────

async def test_moq_race() -> None:
    name = "MoQ atomic counter (10 concurrent increments)"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    request_id = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            await asyncio.gather(*[moq.increment(request_id, 1) for _ in range(10)])
            count = await moq.get_current_count(request_id)

        if count != 10:
            _record_failure(name, f"Expected count=10, got {count}")
            return

        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))
    finally:
        await r.delete(f"moq:count:{request_id}")
        await r.aclose()


# ── 6. Fake email provider ────────────────────────────────────────────────────

async def test_email_fake_provider() -> None:
    name = "Email smoke test (fake provider)"
    try:
        from app.services.email_service import EmailService  # noqa: PLC0415

        result = EmailService.send_email(
            to="smoke@test.local",
            subject="Smoke test",
            html="<p>ok</p>",
        )
        provider = settings.EMAIL_PROVIDER.lower()
        if provider == "fake":
            if result.get("status") != "fake":
                _record_failure(name, f"Expected status='fake', got: {result}")
                return
        _pass(f"{name} (provider={provider}, status={result.get('status')})")
    except Exception as exc:
        _record_failure(name, str(exc))


# ── 7. Notification unique constraint ─────────────────────────────────────────

async def test_notification_unique_constraint() -> None:
    name = "Notification unique constraint (uq_notification_user_request_type)"
    try:
        async with AsyncSessionLocal() as db:
            user = User(
                email=f"smoke-notif-{uuid.uuid4()}@test.local",
                hashed_password=get_password_hash("testpass"),
                is_active=True,
            )
            db.add(user)
            await db.flush()

            product = ProductRequest(title="Notif Constraint Test", status="active")
            db.add(product)
            await db.flush()

            n1 = Notification(
                user_id=user.id,
                request_id=product.id,
                type="moq_reached",
                channel="email",
                status="pending",
            )
            db.add(n1)
            await db.flush()

            n2 = Notification(
                user_id=user.id,
                request_id=product.id,
                type="moq_reached",
                channel="email",
                status="pending",
            )
            db.add(n2)
            try:
                await db.flush()
                await db.commit()
                _record_failure(name, "Duplicate notification was allowed – constraint not working")
                return
            except IntegrityError:
                await db.rollback()
                # Expected – constraint correctly prevented duplicate

        _pass(name)
    except Exception as exc:
        _record_failure(name, str(exc))


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    _log("=" * 60)
    _log("Toplu Alışveriş – smoke & concurrency test suite")
    _log("=" * 60)

    # Ensure tables exist (migrations should have run via alembic upgrade head,
    # but create_all is idempotent and safe as a fallback in local dev runs).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    tests = [
        test_db_connectivity,
        test_redis_connectivity,
        test_wishlist_concurrency,
        test_redis_ttl,
        test_moq_race,
        test_email_fake_provider,
        test_notification_unique_constraint,
    ]

    for test_fn in tests:
        try:
            await test_fn()
        except Exception as exc:  # noqa: BLE001
            _log(f"[{FAIL}] Unhandled exception in {test_fn.__name__}: {exc}")

    _log("=" * 60)
    if _failures:
        _log(f"\n{len(_failures)} test(s) FAILED:")
        for f in _failures:
            _log(f"  - {f}")
        _log("")
        sys.exit(1)
    else:
        _log(f"All {len(tests)} tests PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
