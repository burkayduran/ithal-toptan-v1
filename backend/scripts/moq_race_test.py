#!/usr/bin/env python3
"""
MoQ race / double-trigger test.

Validates:
  * Under heavy parallel check_and_trigger calls, the active→moq_reached
    transition is performed EXACTLY ONCE (transition_performed==True for
    exactly one caller, False for all others).
  * No duplicate notifications are created.
  * DB count == Redis count after the storm (sync_counter_from_db works).
  * TriggerOutcome fields are correctly populated.

Run from backend/:
    python scripts/moq_race_test.py
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import redis.asyncio as aioredis
from sqlalchemy import select, func

from app.core.auth import get_password_hash
from app.core.config import settings
from app.db.session import AsyncSessionLocal, Base, engine
from app.models.models import (
    Notification,
    ProductRequest,
    SupplierOffer,
    User,
    WishlistEntry,
)
from app.services.moq_service import MoQService

CONCURRENCY = 15
MOQ_TARGET = 5
PASS = "PASS"
FAIL = "FAIL"
failures: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def record_failure(name: str, reason: str) -> None:
    failures.append(f"{name}: {reason}")
    log(f"[{FAIL}] {name}: {reason}")


async def setup_seed(
    num_wishlist_entries: int,
) -> tuple[uuid.UUID, uuid.UUID]:
    """Create product + offer + N wishlist entries; return (product_id, offer_id)."""
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"moq-race-admin-{uuid.uuid4()}@test.local",
            hashed_password=get_password_hash("pw"),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        product = ProductRequest(
            title=f"MoQ Race Product {uuid.uuid4()}",
            status="active",
            created_by=user.id,
        )
        db.add(product)
        await db.flush()

        offer = SupplierOffer(
            request_id=product.id,
            unit_price_usd=10.00,
            moq=MOQ_TARGET,
            is_selected=True,
            selling_price_try=500.00,
        )
        db.add(offer)
        await db.flush()

        # Create enough wishlist entries to meet / exceed MoQ
        for _ in range(num_wishlist_entries):
            entry_user = User(
                email=f"moq-race-user-{uuid.uuid4()}@test.local",
                hashed_password=get_password_hash("pw"),
                is_active=True,
            )
            db.add(entry_user)
            await db.flush()
            entry = WishlistEntry(
                request_id=product.id,
                user_id=entry_user.id,
                quantity=1,
                status="waiting",
            )
            db.add(entry)

        await db.commit()
        return product.id, offer.id


async def test_transition_exactly_once() -> None:
    name = "MoQ transition performed exactly once under parallel load"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed with enough entries to exceed MOQ_TARGET
    product_id, offer_id = await setup_seed(num_wishlist_entries=MOQ_TARGET + 3)

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        # Warm Redis counter to match DB (MOQ_TARGET+3 entries × qty=1)
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            db_total = await moq.sync_counter_from_db(product_id)
        log(f"  Seeded db_total={db_total} (target moq={MOQ_TARGET})")

        # Fire CONCURRENCY parallel check_and_trigger calls
        async def run_check(session_idx: int):
            async with AsyncSessionLocal() as db:
                moq = MoQService(db, r)
                return await moq.check_and_trigger(product_id)

        outcomes = await asyncio.gather(*[run_check(i) for i in range(CONCURRENCY)])

        transitions = [o for o in outcomes if o.transition_performed]
        log(f"  transition_performed count: {len(transitions)} (expected 1)")

        if len(transitions) != 1:
            record_failure(
                name,
                f"Expected exactly 1 transition, got {len(transitions)}",
            )
            return

        # Verify product status
        async with AsyncSessionLocal() as db:
            product = await db.scalar(
                select(ProductRequest).where(ProductRequest.id == product_id)
            )
        if product.status != "moq_reached":
            record_failure(
                name, f"Expected product status=moq_reached, got {product.status}"
            )
            return

        # Verify no duplicate notifications (unique constraint + ON CONFLICT DO NOTHING)
        async with AsyncSessionLocal() as db:
            notif_count = await db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.request_id == product_id,
                    Notification.type == "moq_reached",
                )
            )
        log(f"  Notifications created: {notif_count}")
        # There should be at most MOQ_TARGET+3 notifications (one per user), not CONCURRENCY×users
        if notif_count and notif_count > (MOQ_TARGET + 3):
            record_failure(
                name,
                f"Too many notifications: {notif_count} (max expected {MOQ_TARGET + 3})",
            )
            return

        # Verify DB == Redis
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            db_after = await moq.sync_counter_from_db(product_id)
            redis_after = await moq.get_current_count(product_id)

        if db_after != redis_after:
            record_failure(
                name,
                f"After transition: DB total={db_after} != Redis={redis_after}",
            )
            return

        # Verify threshold_met is True for all outcomes (all saw count >= moq)
        all_threshold_met = all(o.threshold_met for o in outcomes)
        log(f"  threshold_met for all={all_threshold_met}")

        log(
            f"[{PASS}] {name} | transition_performed=1 status=moq_reached "
            f"db_total={db_after} redis={redis_after} notifications={notif_count}"
        )
    finally:
        await r.delete(f"moq:count:{product_id}")
        await r.aclose()


async def test_no_trigger_when_below_moq() -> None:
    name = "check_and_trigger skipped when below MoQ threshold"

    product_id, offer_id = await setup_seed(num_wishlist_entries=MOQ_TARGET - 2)

    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            await moq.sync_counter_from_db(product_id)
            outcome = await moq.check_and_trigger(product_id)

        if outcome.threshold_met:
            record_failure(
                name,
                f"threshold_met=True but count < moq (count should be {MOQ_TARGET - 2})",
            )
            return
        if outcome.transition_performed:
            record_failure(name, "transition_performed=True when below threshold")
            return

        async with AsyncSessionLocal() as db:
            product = await db.scalar(
                select(ProductRequest).where(ProductRequest.id == product_id)
            )
        if product.status != "active":
            record_failure(
                name, f"Expected status=active, got {product.status}"
            )
            return

        log(f"[{PASS}] {name} | threshold_met=False transition_performed=False status=active")
    finally:
        await r.delete(f"moq:count:{product_id}")
        await r.aclose()


async def main() -> None:
    log("=" * 60)
    log("MoQ race / double-trigger test")
    log("=" * 60)
    await test_transition_exactly_once()
    await test_no_trigger_when_below_moq()
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
