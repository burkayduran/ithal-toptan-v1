"""
Celery MoQ Tasks
Background jobs for MoQ cleanup and processing
"""
from datetime import datetime, timezone
from sqlalchemy import select, and_
from uuid import UUID

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.models import ProductRequest, WishlistEntry
from app.services.moq_service import MoQService
from app.tasks.email_tasks import send_moq_failed_email
import redis.asyncio as aioredis
from app.core.config import settings


@celery_app.task(name="app.tasks.moq_tasks.cleanup_expired_entries")
def cleanup_expired_entries(request_id: str):
    """
    Cleanup expired entries for a specific product.
    Called 48 hours after MoQ reached.
    
    Args:
        request_id: Product request UUID
    """
    import asyncio
    asyncio.run(_cleanup_expired_entries_async(request_id))


async def _cleanup_expired_entries_async(request_id: str):
    """Async implementation of cleanup."""
    request_uuid = UUID(request_id)
    
    async with AsyncSessionLocal() as db:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        
        try:
            moq_service = MoQService(db, redis_client)
            
            print(f"🧹 Cleaning up expired entries for {request_id}...")
            
            await moq_service.process_expired_entries(request_uuid)
            
            # Check result
            product_result = await db.execute(
                select(ProductRequest).where(ProductRequest.id == request_uuid)
            )
            product = product_result.scalar_one_or_none()
            
            if product:
                if product.status == "ordered":
                    print(f"✅ MoQ success! Product {request_id} ordered")
                elif product.status == "active":
                    print(f"❌ MoQ failed! Product {request_id} reset to active")
                    # Send failure emails
                    send_moq_failed_email.delay(request_id)
        
        finally:
            await redis_client.aclose()


@celery_app.task(name="app.tasks.moq_tasks.cleanup_all_expired")
def cleanup_all_expired():
    """
    Cleanup all expired entries.
    Runs every 30 minutes via Celery Beat.
    """
    import asyncio
    asyncio.run(_cleanup_all_expired_async())


async def _cleanup_all_expired_async():
    """Async implementation of cleanup all."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        
        # Find products with expired deadline
        result = await db.execute(
            select(ProductRequest).where(
                and_(
                    ProductRequest.status == "moq_reached",
                    ProductRequest.payment_deadline.isnot(None),
                    ProductRequest.payment_deadline < now
                )
            )
        )
        expired_products = result.scalars().all()
        
        if not expired_products:
            print("⚠️ No expired products to cleanup")
            return
        
        print(f"🧹 Found {len(expired_products)} expired products. Cleaning up...")
        
        for product in expired_products:
            cleanup_expired_entries.delay(str(product.id))
        
        print(f"✅ Scheduled cleanup for {len(expired_products)} products")
