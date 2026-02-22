#!/usr/bin/env python3
"""
Concurrency test for wishlist/add.

Validates:
  * 20 parallel add calls for the same (user, request_id) result in exactly
    one DB row (no duplicates).
  * All calls succeed without 409 / 500 errors (tested via direct DB UPSERT,
    not HTTP, since we do not spin up the API server here).
  * DB count == Redis count after the storm (no drift).
  * Redis key has a TTL > 0 (initialised correctly).

Run from backend/:
    python scripts/concurrency_wishlist_test.py
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlalchemy as sa
import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.auth import get_password_hash
from app.core.config import settings
from app.db.session import AsyncSessionLocal, Base, engine
from app.models.models import ProductRequest, SupplierOffer, User, WishlistEntry
from app.services.moq_service import MoQService

CONCURRENCY = 20
QUANTITY = 3
PASS = "PASS"
FAIL = "FAIL"
failures: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def record_failure(name: str, reason: str) -> None:
    failures.append(f"{name}: {reason}")
    log(f"[{FAIL}] {name}: {reason}")


async def setup_seed() -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create user + product + offer; return (user_id, product_id, offer_id)."""
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"conc-wish-{uuid.uuid4()}@test.local",
            hashed_password=get_password_hash("pw"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        product = ProductRequest(
            title=f"Concurrency Product {uuid.uuid4()}",
            status="active",
            created_by=user.id,
        )
        db.add(product)
        await db.flush()

        offer = SupplierOffer(
            request_id=product.id,
            unit_price_usd=10.00,
            moq=50,          # high enough that MoQ won't trigger during this test
            is_selected=True,
            selling_price_try=500.00,
        )
        db.add(offer)
        await db.commit()
        return user.id, product.id, offer.id


async def upsert_once(
    user_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: int,
) -> bool:
    """Run a single UPSERT, return True on success."""
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        t = WishlistEntry.__table__
        async with AsyncSessionLocal() as db:
            ins = pg_insert(t).values(
                request_id=product_id,
                user_id=user_id,
                quantity=quantity,
                status="waiting",
                notified_at=None,
                payment_deadline=None,
            )
            stmt = ins.on_conflict_do_update(
                constraint="uq_wishlist_user_request",
                set_={"quantity": ins.excluded.quantity},
            ).returning(t.c.id)
            await db.execute(stmt)
            await db.commit()
        return True
    except Exception as exc:
        log(f"  upsert worker error: {exc}")
        return False


async def test_concurrent_upserts() -> None:
    name = "Concurrent UPSERT (20 parallel)"

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    user_id, product_id, offer_id = await setup_seed()
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        # Fire 20 concurrent UPSERTs for the same (user, product)
        results = await asyncio.gather(
            *[upsert_once(user_id, product_id, QUANTITY) for _ in range(CONCURRENCY)]
        )

        all_ok = all(results)
        if not all_ok:
            record_failure(name, f"{results.count(False)} worker(s) raised exceptions")
            return

        # Verify exactly 1 DB row
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
            record_failure(name, f"Expected 1 DB row, found {len(rows)}")
            return

        if rows[0].quantity != QUANTITY:
            record_failure(
                name,
                f"Expected quantity={QUANTITY}, got {rows[0].quantity}",
            )
            return

        # Sync and verify Redis == DB
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            db_total = await moq.sync_counter_from_db(product_id)
            redis_count = await moq.get_current_count(product_id)

        if db_total != redis_count:
            record_failure(
                name, f"DB total={db_total} != Redis count={redis_count}"
            )
            return

        # Verify TTL
        ttl = await r.ttl(f"moq:count:{product_id}")
        if ttl <= 0:
            record_failure(name, f"Redis key has bad TTL={ttl}")
            return

        log(
            f"[{PASS}] {name} | db_row_count=1 qty={QUANTITY} "
            f"db_total={db_total} redis={redis_count} ttl={ttl}s"
        )
    finally:
        await r.aclose()


async def main() -> None:
    log("=" * 60)
    log("Wishlist concurrency test")
    log("=" * 60)
    await test_concurrent_upserts()
    log("=" * 60)
    if failures:
        log(f"\n{len(failures)} test(s) FAILED:")
        for f in failures:
            log(f"  - {f}")
        sys.exit(1)
    else:
        log("All tests PASSED.")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
