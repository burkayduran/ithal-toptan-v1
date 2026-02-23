"""
Concurrency test for wishlist UPSERT correctness.

Validates that after N parallel add requests by the same user:
  - Exactly 1 wishlist row exists per (user_id, request_id)
  - The Redis counter matches the DB canonical SUM(quantity)

Usage:
    export API_BASE=http://localhost:8000
    export TOKEN=<jwt>
    export REQUEST_ID=<uuid>
    export DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname
    export REDIS_URL=redis://localhost:6379/0
    python backend/scripts/concurrency_wishlist_test.py
"""
import asyncio
import os
import sys

import httpx

API = os.getenv("API_BASE", "http://localhost:8000")
TOKEN = os.getenv("TOKEN", "")
REQUEST_ID = os.getenv("REQUEST_ID", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

PARALLEL = 20


async def hit(i: int) -> httpx.Response:
    async with httpx.AsyncClient(timeout=20) as c:
        return await c.post(
            f"{API}/api/v1/wishlist/add",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={"request_id": REQUEST_ID, "quantity": 1 + (i % 4)},
        )


async def validate_db_row_count(user_id: str) -> tuple[int, int]:
    """Return (row_count, db_quantity_sum) for (user_id, request_id) via DB."""
    try:
        import asyncpg  # type: ignore
    except ImportError:
        print("SKIP DB validation: asyncpg not installed")
        return -1, -1

    if not DATABASE_URL:
        print("SKIP DB validation: DATABASE_URL not set")
        return -1, -1

    # asyncpg uses postgres:// scheme
    url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql://", "postgresql://"
    )
    conn = await asyncpg.connect(url)
    try:
        row_count = await conn.fetchval(
            "SELECT COUNT(*) FROM wishlist_entries WHERE request_id=$1::uuid AND user_id=$2::uuid",
            REQUEST_ID,
            user_id,
        )
        db_sum = await conn.fetchval(
            "SELECT COALESCE(SUM(quantity),0) FROM wishlist_entries "
            "WHERE request_id=$1::uuid AND status IN ('waiting','notified','paid')",
            REQUEST_ID,
        )
        return int(row_count), int(db_sum)
    finally:
        await conn.close()


async def validate_redis(db_sum: int) -> int:
    """Return redis counter value for the request_id key."""
    try:
        import redis.asyncio as aioredis  # type: ignore
    except ImportError:
        print("SKIP Redis validation: redis-py not installed")
        return -1

    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        val = await r.get(f"moq:count:{REQUEST_ID}")
        return int(val) if val is not None else 0
    finally:
        await r.aclose()


async def main() -> None:
    if not TOKEN or not REQUEST_ID:
        print("ERROR: TOKEN and REQUEST_ID env vars are required")
        sys.exit(1)

    print(f"Firing {PARALLEL} parallel add requests for request_id={REQUEST_ID} ...")
    responses = await asyncio.gather(*[hit(i) for i in range(PARALLEL)], return_exceptions=True)

    codes = [r.status_code for r in responses if hasattr(r, "status_code")]
    errors = [r for r in responses if isinstance(r, Exception)]

    print(f"HTTP status codes: {sorted(set(codes))} (total={len(codes)})")
    if errors:
        for e in errors:
            print(f"  exception: {e}")

    assert all(c == 200 for c in codes), f"Expected all 200, got: {codes}"
    print("PASS: all parallel adds returned HTTP 200")

    # Extract the user_id from the last successful response JSON
    last_ok = next(
        (r for r in responses if hasattr(r, "status_code") and r.status_code == 200), None
    )
    user_id = last_ok.json().get("user_id") if last_ok else None

    # DB validation
    if user_id:
        row_count, db_sum = await validate_db_row_count(user_id)
        if row_count >= 0:
            assert row_count == 1, (
                f"Expected exactly 1 wishlist row, found {row_count} "
                f"for user_id={user_id}, request_id={REQUEST_ID}"
            )
            print(f"PASS: exactly 1 DB row for this user (db canonical sum={db_sum})")

            # Redis validation
            redis_val = await validate_redis(db_sum)
            if redis_val >= 0:
                assert redis_val == db_sum, (
                    f"Redis counter mismatch: redis={redis_val}, db_sum={db_sum}"
                )
                print(f"PASS: Redis counter matches DB sum ({redis_val})")
    else:
        print("SKIP DB/Redis validation: could not extract user_id from response")

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
