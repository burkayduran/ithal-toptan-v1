import logging
import logging.config
from contextlib import asynccontextmanager
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sse_starlette.sse import EventSourceResponse
import asyncio

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import engine
from app.api.v1.endpoints import auth, products, wishlist
from app.api.admin import admin

# ── Logging setup ─────────────────────────────────────────────────────────────

_LOG_FORMAT = (
    "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    if settings.DEBUG
    else "%(levelname)s [%(name)s] %(message)s"
)
logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO, format=_LOG_FORMAT)
logger = logging.getLogger(__name__)

# ── Sentry (optional) ─────────────────────────────────────────────────────────

if settings.SENTRY_DSN:
    import sentry_sdk  # noqa: PLC0415
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.2,
        environment="development" if settings.DEBUG else "production",
    )
    logger.info("Sentry initialised")

# ── Global Redis client (strict startup mode) ─────────────────────────────────

redis_client: aioredis.Redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    global redis_client

    # Redis – fail fast if unreachable
    logger.info("Connecting to Redis at %s …", settings.REDIS_URL)
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

    # DB – verify connectivity (schema is managed by Alembic migrations)
    logger.info("Verifying database connectivity…")
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        logger.info("Database ready.")
    except Exception as exc:
        logger.critical("Database is unreachable at startup: %s", exc)
        raise SystemExit(1) from exc

    yield

    # Shutdown
    logger.info("Shutting down – closing Redis and DB connections.")
    await redis_client.aclose()
    await engine.dispose()


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── Rate limiter ───────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ───────────────────────────────────────────────────────────────────────

_allowed_origins = [settings.FRONTEND_URL]
if settings.EXTRA_CORS_ORIGINS:
    _allowed_origins += [o.strip() for o in settings.EXTRA_CORS_ORIGINS.split(",") if o.strip()]
# Allow localhost only in DEBUG / development mode
if settings.DEBUG:
    _allowed_origins += ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(auth.router,     prefix="/api/v1/auth",     tags=["Authentication"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(wishlist.router, prefix="/api/v1/wishlist", tags=["Wishlist"])
app.include_router(admin.router,    prefix="/api/admin",       tags=["Admin"])


# ── SSE endpoint ───────────────────────────────────────────────────────────────

@app.get("/api/v1/moq/progress/{request_id}")
async def moq_progress_stream(request_id: UUID):
    """Server-Sent Events for real-time MoQ progress updates."""
    async def event_generator():
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"moq:progress:{request_id}")

        from app.services.moq_service import MoQService
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            moq_service = MoQService(db, redis_client)
            current_count = await moq_service.get_current_count(request_id)
            yield {"data": str(current_count)}

        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
                if message:
                    yield {"data": message["data"]}
                await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(f"moq:progress:{request_id}")
            await pubsub.close()

    return EventSourceResponse(event_generator())


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    """Deep health check: verifies DB and Redis connectivity."""
    from sqlalchemy import text

    health: dict = {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}
    errors: list = []

    # DB check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health["db"] = "ok"
    except Exception as exc:
        health["db"] = "error"
        errors.append(f"db: {exc}")

    # Redis check
    try:
        await redis_client.ping()
        health["redis"] = "ok"
    except Exception as exc:
        health["redis"] = "error"
        errors.append(f"redis: {exc}")

    if errors:
        health["status"] = "degraded"
        health["errors"] = errors
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content=health)

    return health


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Toplu Alışveriş Platform API",
        "docs": "/api/docs",
        "health": "/health",
    }
