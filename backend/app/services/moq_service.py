"""
MoQ (Minimum Order Quantity) Service
Redis-based atomic counter and trigger logic
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.core.config import settings
from app.models.models import (
    ProductRequest,
    SupplierOffer,
    WishlistEntry,
    Notification
)


class MoQService:
    """Handle MoQ tracking and payment phase triggering."""
    
    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client
    
    def _get_counter_key(self, request_id: UUID) -> str:
        """Get Redis key for MoQ counter."""
        return f"moq:count:{str(request_id)}"
    
    async def get_current_count(self, request_id: UUID) -> int:
        """Get current wishlist count from Redis (with DB fallback)."""
        # Try Redis first
        count = await self.redis.get(self._get_counter_key(request_id))
        
        if count is not None:
            return int(count)
        
        # Fallback: Calculate from database
        result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0))
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status.in_(["waiting", "notified"])
            )
        )
        db_count = result.scalar() or 0
        
        # Cache in Redis with a 30-day TTL (aligned with max campaign length)
        await self.redis.set(self._get_counter_key(request_id), db_count, ex=30 * 24 * 3600)
        
        return db_count
    
    async def increment(self, request_id: UUID, quantity: int = 1) -> int:
        """Increment MoQ counter atomically."""
        key = self._get_counter_key(request_id)
        new_count = await self.redis.incrby(key, quantity)
        # Set a 30-day TTL only when the key is brand-new (TTL == -1 means no expiry set yet)
        if await self.redis.ttl(key) == -1:
            await self.redis.expire(key, 30 * 24 * 3600)

        # Publish update for SSE
        await self.redis.publish(
            f"moq:progress:{str(request_id)}",
            str(new_count)
        )
        
        return new_count
    
    async def decrement(self, request_id: UUID, quantity: int = 1) -> int:
        """Decrement MoQ counter atomically."""
        key = self._get_counter_key(request_id)
        new_count = await self.redis.decrby(key, quantity)
        
        # Don't go below 0
        if new_count < 0:
            await self.redis.set(key, 0)
            new_count = 0
        
        # Publish update for SSE
        await self.redis.publish(
            f"moq:progress:{str(request_id)}",
            str(new_count)
        )
        
        return new_count
    
    async def check_and_trigger(self, request_id: UUID) -> bool:
        """Check if MoQ is reached and trigger payment phase."""
        # Get current count
        current_count = await self.get_current_count(request_id)
        
        # Get product and offer
        product_result = await self.db.execute(
            select(ProductRequest).where(ProductRequest.id == request_id)
        )
        product = product_result.scalar_one_or_none()
        
        if not product or product.status != "active":
            return False
        
        # Get selected offer
        offer_result = await self.db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_id,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        if not offer:
            return False
        
        # Check if MoQ reached
        if current_count >= offer.moq:
            # Trigger payment phase
            await self.trigger_payment_phase(request_id, offer)
            return True
        
        return False
    
    async def trigger_payment_phase(self, request_id: UUID, offer: SupplierOffer):
        """
        Trigger 48-hour payment window when MoQ is reached.
        """
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=48)
        
        # Update product status
        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(
                status="moq_reached",
                moq_reached_at=now,
                payment_deadline=deadline
            )
        )
        
        # Update all "waiting" entries to "notified"
        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "waiting"
            )
            .values(
                status="notified",
                notified_at=now,
                payment_deadline=deadline
            )
        )
        
        await self.db.commit()
        
        # Schedule email notifications (will be handled by Celery later)
        # For now, just create notification records
        notified_result = await self.db.execute(
            select(WishlistEntry).where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "notified"
            )
        )
        notified_entries = notified_result.scalars().all()
        
        for entry in notified_entries:
            notification = Notification(
                user_id=entry.user_id,
                request_id=request_id,
                type="moq_reached",
                channel="email",
                subject=f"Sipariş hazır! 48 saat içinde ödeme yapın",
                status="pending"
            )
            self.db.add(notification)
        
        await self.db.commit()
        
        # Schedule email notifications
        from app.tasks.email_tasks import send_moq_reached_email
        from app.tasks.moq_tasks import cleanup_expired_entries
        
        # Send emails immediately
        send_moq_reached_email.delay(
            str(request_id),
            deadline.isoformat()
        )
        
        # Schedule cleanup after 48 hours
        cleanup_expired_entries.apply_async(
            args=[str(request_id)],
            countdown=48 * 3600  # 48 hours in seconds
        )
    
    async def process_expired_entries(self, request_id: UUID):
        """
        Process entries after 48-hour deadline.
        Called by Celery task after payment window closes.
        """
        now = datetime.now(timezone.utc)

        # Mark expired entries
        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "notified",
                WishlistEntry.payment_deadline < now
            )
            .values(status="expired")
        )
        
        await self.db.commit()
        
        # Count paid entries
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0))
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "paid"
            )
        )
        paid_count = paid_result.scalar() or 0
        
        # Get offer
        offer_result = await self.db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_id,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        if not offer:
            return
        
        if paid_count >= offer.moq:
            # Success! Create batch order
            await self._create_batch_order(request_id, offer, paid_count)
        else:
            # Failed - reset to active
            await self._reset_to_active(request_id)
    
    async def _create_batch_order(self, request_id: UUID, offer: SupplierOffer, quantity: int):
        """Create batch order after successful payment collection."""
        from app.models.models import BatchOrder
        
        # Calculate totals
        total_cost_usd = float(offer.unit_price_usd) * quantity
        if offer.shipping_cost_usd:
            total_cost_usd += float(offer.shipping_cost_usd)

        batch_order = BatchOrder(
            request_id=request_id,
            offer_id=offer.id,
            total_quantity=quantity,
            total_cost_usd=Decimal(str(total_cost_usd)),
            status="pending"
        )
        
        self.db.add(batch_order)
        
        # Update product status
        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(status="ordered")
        )
        
        await self.db.commit()
        
        # TODO: Notify users about successful order
    
    async def _reset_to_active(self, request_id: UUID):
        """Reset product to active status if MoQ failed."""
        # Update expired entries back to waiting
        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "expired"
            )
            .values(
                status="waiting",
                notified_at=None,
                payment_deadline=None
            )
        )
        
        # Update product back to active
        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(
                status="active",
                moq_reached_at=None,
                payment_deadline=None
            )
        )
        
        await self.db.commit()
        
        # Reset Redis counter (re-sync from DB, preserve 30-day TTL)
        current_count = await self.get_current_count(request_id)
        await self.redis.set(self._get_counter_key(request_id), current_count, ex=30 * 24 * 3600)
        
        # TODO: Notify users that MoQ failed
