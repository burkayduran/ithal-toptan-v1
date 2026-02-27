from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from uuid import UUID
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

from app.core.config import settings
from app.core.redis import create_redis_pool
from app.db.session import engine, Base
from app.api.v1.endpoints import auth, products, wishlist
from app.api.admin import admin
from sse_starlette.sse import EventSourceResponse
import asyncio

# Global rate limiter (key: remote IP)
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Connect to Redis using a shared connection pool
    app.state.redis = create_redis_pool()
    await app.state.redis.ping()

    yield

    # Shutdown: close Redis pool and DB engine
    await app.state.redis.aclose()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Attach limiter so SlowAPI decorators can find it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
async def moq_progress_stream(request_id: UUID, request: Request):
    """
    Server-Sent Events endpoint for real-time MoQ progress updates.
    Frontend can use EventSource to listen for updates.
    """
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Real-time service unavailable")

    async def event_generator():
        # Subscribe to Redis pub/sub channel
        channel = f"moq:progress:{str(request_id)}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        
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
            try:
                await pubsub.unsubscribe(channel)
            except Exception as exc:
                print(f"SSE unsubscribe error: {exc}")
            try:
                await pubsub.close()
            except Exception as exc:
                print(f"SSE pubsub close error: {exc}")
    
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
