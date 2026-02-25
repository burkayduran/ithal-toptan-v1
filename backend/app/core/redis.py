"""
Shared Redis client with connection pooling.
Provides a single async Redis client attached to app.state.redis,
and a FastAPI dependency get_redis() for injection into endpoints/services.
"""
import redis.asyncio as aioredis
from fastapi import Request, HTTPException

from app.core.config import settings


def create_redis_pool() -> aioredis.Redis:
    """
    Create a Redis client backed by a connection pool.
    Call once at startup and store in app.state.redis.
    """
    return aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        max_connections=20,
    )


async def get_redis(request: Request) -> aioredis.Redis:
    """
    FastAPI dependency: inject the shared Redis client.
    Raises 503 if the client is not yet initialised (should not happen in normal operation).
    """
    redis: aioredis.Redis | None = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status_code=503, detail="Redis service unavailable")
    return redis
