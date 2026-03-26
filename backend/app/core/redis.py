"""
Redis connection pool — shared across the application.
"""
import redis.asyncio as aioredis
from app.core.config import settings

redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the shared Redis connection pool."""
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return redis_pool


async def close_redis():
    """Close the Redis connection pool."""
    global redis_pool
    if redis_pool:
        await redis_pool.aclose()
        redis_pool = None
