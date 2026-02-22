#!/usr/bin/env python3
"""
Redis TTL race test.

Validates:
  * Atomic Lua increment initialises the TTL exactly once (even under parallel
    load) and never leaves the key with TTL == -1.
  * Parallel increments produce the exact expected total (no lost updates).
  * Parallel decrements clamp correctly at 0.
  * TTL is preserved (not reset) across multiple increment calls.

Run from backend/:
    python scripts/redis_ttl_race_test.py
"""
import asyncio
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import redis.asyncio as aioredis
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.services.moq_service import MoQService, _TTL_SECS

CONCURRENCY = 30
PASS = "PASS"
FAIL = "FAIL"
failures: list[str] = []


def log(msg: str) -> None:
    print(msg, flush=True)


def record_failure(name: str, reason: str) -> None:
    failures.append(f"{name}: {reason}")
    log(f"[{FAIL}] {name}: {reason}")


async def test_parallel_increments_ttl() -> None:
    name = "Parallel increments – TTL always initialised"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    rid = uuid.uuid4()
    try:
        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            await asyncio.gather(*[moq.increment(rid, 1) for _ in range(CONCURRENCY)])
            count = await moq.get_current_count(rid)

        if count != CONCURRENCY:
            record_failure(name, f"Expected count={CONCURRENCY}, got {count}")
            return

        ttl = await r.ttl(f"moq:count:{rid}")
        if ttl == -1:
            record_failure(name, "TTL was never set (TTL == -1)")
            return
        if ttl <= 0:
            record_failure(name, f"Unexpected TTL={ttl}")
            return

        log(f"[{PASS}] {name} | count={count} ttl={ttl}s (max={_TTL_SECS}s)")
    finally:
        await r.delete(f"moq:count:{rid}")
        await r.aclose()


async def test_ttl_not_reset_on_subsequent_increments() -> None:
    name = "TTL not reset on subsequent increments"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    rid = uuid.uuid4()
    key = f"moq:count:{rid}"
    try:
        # Pre-set the key with a SHORT known TTL to simulate an already-running campaign
        await r.set(key, 0, ex=100)

        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            for _ in range(5):
                await moq.increment(rid, 1)
            count = await moq.get_current_count(rid)

        ttl = await r.ttl(key)
        # TTL should still be close to 100 (the original), not reset to 30 days
        if ttl > 100:
            record_failure(
                name,
                f"TTL was reset! Expected <=100, got {ttl}",
            )
            return
        if ttl <= 0:
            record_failure(name, f"Key expired prematurely TTL={ttl}")
            return

        log(f"[{PASS}] {name} | count={count} ttl={ttl}s (preserved)")
    finally:
        await r.delete(key)
        await r.aclose()


async def test_parallel_decrements_clamp() -> None:
    name = "Parallel decrements – clamp at 0"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    rid = uuid.uuid4()
    key = f"moq:count:{rid}"
    try:
        await r.set(key, 5, ex=_TTL_SECS)

        async with AsyncSessionLocal() as db:
            moq = MoQService(db, r)
            # Decrement 20 times from an initial value of 5 – result must clamp at 0
            await asyncio.gather(*[moq.decrement(rid, 1) for _ in range(20)])
            count = await moq.get_current_count(rid)

        if count != 0:
            record_failure(name, f"Expected 0 after over-decrement, got {count}")
            return

        log(f"[{PASS}] {name} | count={count}")
    finally:
        await r.delete(key)
        await r.aclose()


async def test_key_expiry() -> None:
    name = "Key expiry (short TTL)"
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    key = f"moq:count:{uuid.uuid4()}"
    try:
        await r.set(key, "42", ex=2)
        val = await r.get(key)
        assert val == "42", f"Expected '42', got '{val}'"

        await asyncio.sleep(3)
        expired = await r.get(key)
        if expired is not None:
            record_failure(name, f"Key should have expired, got '{expired}'")
            return

        log(f"[{PASS}] {name}")
    finally:
        await r.aclose()


async def main() -> None:
    log("=" * 60)
    log("Redis TTL race test")
    log("=" * 60)
    await test_parallel_increments_ttl()
    await test_ttl_not_reset_on_subsequent_increments()
    await test_parallel_decrements_clamp()
    await test_key_expiry()
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
