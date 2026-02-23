"""
MoQ (Minimum Order Quantity) Service
Redis-based atomic counter and trigger logic
"""
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.models import (
    ProductRequest,
    SupplierOffer,
    WishlistEntry,
    Notification
)

logger = logging.getLogger(__name__)


class MoQService:
    """Handle MoQ tracking and payment phase triggering."""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client

    def _get_counter_key(self, request_id: UUID) -> str:
        """Get Redis key for MoQ counter."""
        return f"moq:count:{request_id}"

    async def get_current_count(self, request_id: UUID) -> int:
        """Get current wishlist count from Redis (with DB fallback)."""
        count = await self.redis.get(self._get_counter_key(request_id))

        if count is not None:
            return int(count)

        result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0))
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status.in_(["waiting", "notified", "paid"])
            )
        )
        db_count = result.scalar() or 0

        await self.redis.set(self._get_counter_key(request_id), db_count, ex=30 * 24 * 3600)
        return db_count

    async def increment(self, request_id: UUID, quantity: int = 1) -> int:
        """Increment MoQ counter atomically with TTL bootstrap via Lua."""
        key = self._get_counter_key(request_id)
        script = """
local key = KEYS[1]
local qty = tonumber(ARGV[1])
local ttl_seconds = tonumber(ARGV[2])
local val = redis.call('INCRBY', key, qty)
if redis.call('TTL', key) == -1 then
  redis.call('EXPIRE', key, ttl_seconds)
end
return val
"""
        new_count = int(await self.redis.eval(script, 1, key, quantity, 30 * 24 * 3600))

        await self.redis.publish(f"moq:progress:{request_id}", str(new_count))
        return new_count

    async def decrement(self, request_id: UUID, quantity: int = 1) -> int:
        """Decrement MoQ counter atomically with Lua and floor at zero."""
        key = self._get_counter_key(request_id)
        script = """
local key = KEYS[1]
local qty = tonumber(ARGV[1])
local ttl_seconds = tonumber(ARGV[2])
local val = redis.call('DECRBY', key, qty)
if val < 0 then
  val = 0
  redis.call('SET', key, 0)
end
if redis.call('TTL', key) == -1 then
  redis.call('EXPIRE', key, ttl_seconds)
end
return val
"""
        new_count = int(await self.redis.eval(script, 1, key, quantity, 30 * 24 * 3600))
        await self.redis.publish(f"moq:progress:{request_id}", str(new_count))
        return new_count


    async def sync_counter_from_db(self, request_id: UUID) -> int:
        """Force-sync Redis counter from DB aggregate to avoid drift under concurrent updates."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0))
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status.in_(["waiting", "notified", "paid"])
            )
        )
        db_count = int(result.scalar() or 0)
        await self.redis.set(self._get_counter_key(request_id), db_count, ex=30 * 24 * 3600)
        await self.redis.publish(f"moq:progress:{request_id}", str(db_count))
        return db_count

    async def check_and_trigger(self, request_id: UUID) -> dict:
        """Check threshold and attempt atomic payment-phase transition."""
        current_count = await self.get_current_count(request_id)

        product_result = await self.db.execute(
            select(ProductRequest).where(ProductRequest.id == request_id)
        )
        product = product_result.scalar_one_or_none()

        if not product or product.status != "active":
            return {"threshold_met": False, "transition_performed": False, "status_after": product.status if product else "missing"}

        offer_result = await self.db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_id,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()

        if not offer or offer.moq is None or offer.moq <= 0:
            return {"threshold_met": False, "transition_performed": False, "status_after": product.status}

        threshold_met = current_count >= offer.moq
        if not threshold_met:
            logger.info(
                "check_and_trigger: threshold not met",
                extra={
                    "request_id": str(request_id),
                    "current_count": current_count,
                    "offer_moq": offer.moq,
                    "threshold_met": False,
                    "transition_performed": False,
                },
            )
            return {"threshold_met": False, "transition_performed": False, "status_after": product.status}

        transition_performed = await self.trigger_payment_phase(request_id, offer)

        refreshed = await self.db.execute(select(ProductRequest.status).where(ProductRequest.id == request_id))
        status_after = refreshed.scalar_one_or_none() or product.status
        logger.info(
            "check_and_trigger: threshold met",
            extra={
                "request_id": str(request_id),
                "current_count": current_count,
                "offer_moq": offer.moq,
                "threshold_met": True,
                "transition_performed": transition_performed,
                "status_after": status_after,
            },
        )
        return {"threshold_met": True, "transition_performed": transition_performed, "status_after": status_after}

    async def trigger_payment_phase(self, request_id: UUID, offer: SupplierOffer) -> bool:
        """Trigger 48-hour payment window when MoQ is reached."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=48)

        product_update = await self.db.execute(
            update(ProductRequest)
            .where(
                ProductRequest.id == request_id,
                ProductRequest.status == "active"
            )
            .values(
                status="moq_reached",
                moq_reached_at=now,
                payment_deadline=deadline
            )
        )

        if product_update.rowcount == 0:
            await self.db.rollback()
            return False

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

        notified_result = await self.db.execute(
            select(WishlistEntry).where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "notified"
            )
        )
        notified_entries = notified_result.scalars().all()

        existing_notif_result = await self.db.execute(
            select(Notification.user_id).where(
                Notification.request_id == request_id,
                Notification.type == "moq_reached",
                Notification.channel == "email",
                Notification.status.in_(["pending", "sent", "delivered", "opened", "clicked"]),
            )
        )
        existing_user_ids = {row[0] for row in existing_notif_result.all()}

        for entry in notified_entries:
            if entry.user_id in existing_user_ids:
                continue
            self.db.add(
                Notification(
                    user_id=entry.user_id,
                    request_id=request_id,
                    type="moq_reached",
                    channel="email",
                    subject="Sipariş hazır! 48 saat içinde ödeme yapın",
                    status="pending"
                )
            )

        await self.db.commit()

        from app.tasks.email_tasks import send_moq_reached_email
        from app.tasks.moq_tasks import cleanup_expired_entries

        send_moq_reached_email.delay(str(request_id), deadline.isoformat())
        cleanup_expired_entries.apply_async(args=[str(request_id)], countdown=48 * 3600)

        return True

    async def process_expired_entries(self, request_id: UUID):
        """Process entries after 48-hour deadline."""
        now = datetime.now(timezone.utc)

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

        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0))
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "paid"
            )
        )
        paid_count = paid_result.scalar() or 0

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
            await self._create_batch_order(request_id, offer, paid_count)
        else:
            await self._reset_to_active(request_id)

    async def _create_batch_order(self, request_id: UUID, offer: SupplierOffer, quantity: int):
        from app.models.models import BatchOrder

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

        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(status="ordered")
        )

        await self.db.commit()

    async def _reset_to_active(self, request_id: UUID):
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

        current_count = await self.get_current_count(request_id)
        await self.redis.set(self._get_counter_key(request_id), current_count, ex=30 * 24 * 3600)
