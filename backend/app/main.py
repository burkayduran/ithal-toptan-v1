from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
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

# Global Redis connection for SSE.
# STRICT MODE: redis_client is always set after startup or the process has exited.
redis_client: aioredis.Redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events.

    Strict Redis mode: if Redis is unreachable at startup the application
    raises immediately, preventing a partially-functional deployment.
    """
    global redis_client

    # Startup: Create DB tables
    logger.info("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")

    # Startup: Connect to Redis — fail fast if unreachable
    logger.info("Connecting to Redis at %s ...", settings.REDIS_URL)
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis_client.ping()
    except Exception as exc:
        logger.critical(
            "Redis is unreachable at startup (%s). "
            "The application requires Redis for MoQ counters and real-time updates. "
            "Fix the connection and restart.",
            exc,
        )
        raise SystemExit(1) from exc
    logger.info("Redis ready.")

    yield

    # Shutdown
    logger.info("Shutting down — closing Redis and DB connections.")
    await redis_client.aclose()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
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
async def moq_progress_stream(request_id: UUID):
    """
    Server-Sent Events endpoint for real-time MoQ progress updates.
    Frontend can use EventSource to listen for updates.

    Redis is guaranteed to be available (strict startup mode).
    """
    async def event_generator():
        # Subscribe to Redis pub/sub channel
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"moq:progress:{str(request_id)}")
        
        # Send initial value
        from app.services.moq_service import MoQService
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            moq_service = MoQService(db, redis_client)
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
            # Always clean up the pubsub connection regardless of how the generator exits
            # (client disconnect → CancelledError, normal exit, or any other exception).
            await pubsub.unsubscribe(f"moq:progress:{str(request_id)}")
            await pubsub.close()
    
    return EventSourceResponse(event_generator())


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Toplu Alışveriş Platform API",
        "docs": "/api/docs",
        "health": "/health"
    }
