"""Stress-test the Lua INCRBY+EXPIRE script for atomic TTL bootstrap.

Requires Redis.  Set REDIS_URL env var if Redis is not on localhost:6379.

  REDIS_URL=redis://myhost:6379/0 python backend/scripts/redis_ttl_race_test.py
"""
import asyncio
import os
import sys
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
KEY = "moq:count:test-race"

LUA = """
local newVal = redis.call('INCRBY', KEYS[1], ARGV[1])
local ttl = redis.call('TTL', KEYS[1])
if ttl == -1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
return newVal
"""


async def worker(r: aioredis.Redis):
    await r.eval(LUA, 1, KEY, 1, 30 * 24 * 3600)


async def main():
    r = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await r.ping()
    except Exception as exc:
        print(
            f"ERROR: Cannot connect to Redis at {REDIS_URL!r}.\n"
            f"  Set REDIS_URL to a reachable Redis instance and retry.\n"
            f"  Details: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    await r.delete(KEY)
    await asyncio.gather(*[worker(r) for _ in range(200)])
    val = int(await r.get(KEY) or 0)
    ttl = await r.ttl(KEY)
    print("val", val, "ttl", ttl)
    assert val == 200, f"Expected 200, got {val}"
    assert ttl and ttl > 0, f"Expected positive TTL, got {ttl}"
    print("OK: Lua INCRBY+EXPIRE is atomic under 200 parallel workers")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
