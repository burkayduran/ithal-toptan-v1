from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.core.redis import get_redis, close_redis

# Initialize logging
setup_logging()
from app.db.session import engine
from app.api.v1.endpoints import auth, products, wishlist, payments
from app.api.admin import admin
from app.api.v2 import campaigns as v2_campaigns, suggestions as v2_suggestions, payments as v2_payments
from app.api.admin import admin_v2
from sse_starlette.sse import EventSourceResponse
import asyncio
import logging

logger = logging.getLogger("ithal_toptan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Initialize Redis pool and verify
    redis_client = await get_redis()
    await redis_client.ping()

    logger.info("Application startup complete")

    yield

    # Shutdown
    await close_redis()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# V2 routers
app.include_router(v2_campaigns.router, prefix="/api/v2/campaigns", tags=["V2 Campaigns"])
app.include_router(v2_suggestions.router, prefix="/api/v2/suggestions", tags=["V2 Suggestions"])
app.include_router(v2_payments.router, prefix="/api/v2/payments", tags=["V2 Payments"])
app.include_router(admin_v2.router, prefix="/api/v2/admin", tags=["V2 Admin"])


# SSE endpoint for real-time MoQ progress
_SSE_ALLOWED_STATUSES = {"active", "moq_reached", "payment_collecting", "ordered", "delivered"}

@app.get("/api/v1/moq/progress/{request_id}")
@limiter.limit("30/minute")
async def moq_progress_stream(request: Request, request_id: UUID):
    """
    Server-Sent Events endpoint for real-time MoQ progress updates.
    Frontend can use EventSource to listen for updates.
    Only publicly visible products (non-draft) are accessible.
    """
    redis_client = await get_redis()

    from app.db.session import AsyncSessionLocal
    from app.models.models import ProductRequest
    from sqlalchemy import select as sa_select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            sa_select(ProductRequest.status).where(ProductRequest.id == request_id)
        )
        row = result.scalar_one_or_none()
        if row is None or row not in _SSE_ALLOWED_STATUSES:
            raise HTTPException(status_code=404, detail="Not found")

    async def event_generator():
        # Subscribe to Redis pub/sub channel
        channel = f"moq:progress:{str(request_id)}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        # Send initial value
        from app.services.moq_service import MoQService

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
            try:
                await pubsub.unsubscribe(channel)
            except Exception as exc:
                logger.warning("SSE unsubscribe error: %s", exc)
            try:
                await pubsub.close()
            except Exception as exc:
                logger.warning("SSE pubsub close error: %s", exc)

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
