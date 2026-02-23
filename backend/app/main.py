from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID

from app.core.config import settings
from app.db.session import engine, Base
from app.api.v1.endpoints import auth, products, wishlist
from app.api.admin import admin
import redis.asyncio as aioredis
from sse_starlette.sse import EventSourceResponse
import asyncio

logger = logging.getLogger(__name__)

# Global Redis connection for SSE and shared use
redis_client: aioredis.Redis = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    global redis_client

    # create_all() is only allowed in development/local to avoid schema drift
    # with Alembic.  In staging/production, run `alembic upgrade head` instead.
    _dev_envs = ("development", "local")
    if settings.ENVIRONMENT in _dev_envs:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(
            "create_all() ran (ENVIRONMENT=%s). "
            "Tables created/verified via SQLAlchemy metadata.",
            settings.ENVIRONMENT,
        )
    else:
        logger.info(
            "create_all() SKIPPED (ENVIRONMENT=%s). "
            "Schema must be managed via: alembic upgrade head",
            settings.ENVIRONMENT,
        )

    # Create one shared Redis client for the lifetime of the process.
    # All endpoints and services borrow this client; it is never closed
    # per-request.
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    await redis_client.ping()
    app.state.redis = redis_client
    logger.info("Redis connected: %s", settings.REDIS_URL)

    yield

    # Shutdown
    if redis_client:
        await redis_client.aclose()
    await engine.dispose()
    logger.info("Redis and DB engine closed.")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(wishlist.router, prefix="/api/v1/wishlist", tags=["Wishlist"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


# SSE endpoint for real-time MoQ progress
@app.get("/api/v1/moq/progress/{request_id}")
async def moq_progress_stream(request: Request, request_id: UUID):
    """
    Server-Sent Events endpoint for real-time MoQ progress updates.
    Frontend can use EventSource to listen for updates.
    """
    shared_redis: aioredis.Redis = request.app.state.redis
    if shared_redis is None:
        raise HTTPException(status_code=503, detail="Real-time service unavailable")

    async def event_generator():
        # Subscribe to Redis pub/sub channel
        channel = f"moq:progress:{str(request_id)}"
        pubsub = shared_redis.pubsub()
        await pubsub.subscribe(channel)

        # Send initial value
        from app.services.moq_service import MoQService
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            moq_service = MoQService(db, shared_redis)
            current_count = await moq_service.get_current_count(request_id)
            yield {"data": str(current_count)}

        # Listen for updates
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if message:
                    yield {"data": message["data"]}
                await asyncio.sleep(0.1)
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception as exc:
                logger.exception("SSE unsubscribe error for request_id=%s: %s", request_id, exc)
            try:
                await pubsub.close()
            except Exception as exc:
                logger.exception("SSE pubsub close error for request_id=%s: %s", request_id, exc)

    return EventSourceResponse(event_generator())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "İthal Toptan 2.0 API",
        "docs": "/api/docs",
        "health": "/health"
    }
