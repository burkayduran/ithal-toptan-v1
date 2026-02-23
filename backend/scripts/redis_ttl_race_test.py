"""
Redis Lua TTL race test.

Validates that concurrent INCRBY / DECRBY Lua calls:
  - Always result in a TTL > 0 (key is never left without expiry)
  - Produce the correct final counter value
  - Decrement never leaves a negative value (floor at 0)

Requires a running Redis instance.

Usage:
    export REDIS_URL=redis://localhost:6379/0
    python backend/scripts/redis_ttl_race_test.py
"""
import asyncio
import os

import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY_INCR = "moq:count:test-race-incr"
KEY_DECR = "moq:count:test-race-decr"
TTL_SECONDS = 30 * 24 * 3600

LUA_INCR = """
local newVal = redis.call('INCRBY', KEYS[1], ARGV[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl == -1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return newVal
"""

LUA_DECR = """
local key = KEYS[1]
local qty = tonumber(ARGV[1])
local ttl_seconds = tonumber(ARGV[2])
local val = redis.call('DECRBY', key, qty)
if val < 0 then
  val = 0
  redis.call('SET', key, 0)
end
if redis.call('TTL', key) == -1 then
  redis.call('EXPIRE', key, ttl_seconds)
end
return val
"""


async def incr_worker(r: aioredis.Redis, qty: int = 1) -> None:
    await r.eval(LUA_INCR, 1, KEY_INCR, qty, TTL_SECONDS)


async def decr_worker(r: aioredis.Redis, qty: int = 1) -> None:
    await r.eval(LUA_DECR, 1, KEY_DECR, qty, TTL_SECONDS)


async def main() -> None:
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    # ── Test 1: 200 concurrent increments ───────────────────────────────────
    await r.delete(KEY_INCR)
    await asyncio.gather(*[incr_worker(r) for _ in range(200)])
    val = int(await r.get(KEY_INCR) or 0)
    ttl = await r.ttl(KEY_INCR)
    print(f"[incr] val={val}  ttl={ttl}")
    assert val == 200, f"Expected 200, got {val}"
    assert ttl > 0, f"Expected TTL > 0, got {ttl}"
    print("PASS: 200 concurrent increments → correct count and TTL is set")

    # ── Test 2: decrement floor at zero ──────────────────────────────────────
    # Seed the key at 10, then decrement 50 times (would go to -40 without floor)
    await r.delete(KEY_DECR)
    await r.set(KEY_DECR, 10)
    await asyncio.gather(*[decr_worker(r) for _ in range(50)])
    val = int(await r.get(KEY_DECR) or 0)
    ttl = await r.ttl(KEY_DECR)
    print(f"[decr] val={val}  ttl={ttl}")
    assert val == 0, f"Expected 0 (floor), got {val}"
    print("PASS: decrement floor at zero — counter never goes negative")

    # ── Test 3: TTL is initialised on a key that had no expiry ───────────────
    await r.delete(KEY_INCR)
    await r.set(KEY_INCR, 0)  # key exists but has no TTL (-1)
    assert await r.ttl(KEY_INCR) == -1, "Precondition: key has no TTL"
    await r.eval(LUA_INCR, 1, KEY_INCR, 1, TTL_SECONDS)
    ttl = await r.ttl(KEY_INCR)
    assert ttl > 0, f"Expected TTL to be set after first eval, got {ttl}"
    print("PASS: TTL is initialised on a key that previously had no expiry")

    await r.aclose()
    print("ALL REDIS TTL RACE TESTS PASSED")


if __name__ == "__main__":
    asyncio.run(main())
