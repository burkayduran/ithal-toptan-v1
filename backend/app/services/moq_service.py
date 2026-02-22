"""
MoQ (Minimum Order Quantity) Service
Redis-based atomic counter and trigger logic.

Key guarantees
──────────────
* Increment / decrement: Lua script ensures INCRBY + TTL-init is a single
  atomic operation on the Redis side, so concurrent callers never corrupt the
  counter or leave a key without a TTL.
* sync_counter_from_db(): recalculates the canonical count from Postgres and
  writes it to Redis, then publishes it on the SSE channel.  Called after
  every wishlist write so DB and Redis can never stay out of sync for long.
* check_and_trigger(): uses an UPDATE ... WHERE status='active' guard so that
  the active→moq_reached transition is performed at most once regardless of
  how many workers run check_and_trigger concurrently.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    BatchOrder,
    Notification,
    ProductRequest,
    SupplierOffer,
    WishlistEntry,
)

logger = logging.getLogger(__name__)

_TTL_SECS = 30 * 24 * 3600  # 30-day campaign TTL

# ── Lua scripts ───────────────────────────────────────────────────────────────
# Both scripts initialise the TTL only when the key has no expiry yet (TTL==-1),
# which prevents resetting a running campaign counter's TTL on every write.

_LUA_INCR = """
local key      = KEYS[1]
local qty      = tonumber(ARGV[1])
local ttl_secs = tonumber(ARGV[2])
local new_val  = redis.call('INCRBY', key, qty)
if redis.call('TTL', key) == -1 then
    redis.call('EXPIRE', key, ttl_secs)
end
return new_val
"""

_LUA_DECR = """
local key      = KEYS[1]
local qty      = tonumber(ARGV[1])
local ttl_secs = tonumber(ARGV[2])
local new_val  = redis.call('DECRBY', key, qty)
if new_val < 0 then
    redis.call('SET', key, '0')
    new_val = 0
end
if redis.call('TTL', key) == -1 then
    redis.call('EXPIRE', key, ttl_secs)
end
return new_val
"""


# ── Outcome dataclass ─────────────────────────────────────────────────────────

@dataclass
class TriggerOutcome:
    """Structured result from check_and_trigger()."""
    threshold_met: bool
    transition_performed: bool
    status_after: str


# ── MoQService ────────────────────────────────────────────────────────────────

class MoQService:
    """Handle MoQ tracking and payment-phase triggering."""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client

    # ── counter key helpers ────────────────────────────────────────────────────

    def _counter_key(self, request_id: UUID) -> str:
        return f"moq:count:{request_id}"

    def _sse_channel(self, request_id: UUID) -> str:
        return f"moq:progress:{request_id}"

    # ── legacy alias kept for backwards compatibility ──────────────────────────
    def _get_counter_key(self, request_id: UUID) -> str:
        return self._counter_key(request_id)

    # ── read counter ──────────────────────────────────────────────────────────

    async def get_current_count(self, request_id: UUID) -> int:
        """Return Redis counter, falling back to a DB sync if the key is missing."""
        raw = await self.redis.get(self._counter_key(request_id))
        if raw is not None:
            return int(raw)
        # Key missing → warm from DB and cache
        return await self.sync_counter_from_db(request_id)

    # ── atomic increment (Lua) ────────────────────────────────────────────────

    async def increment(self, request_id: UUID, quantity: int = 1) -> int:
        """
        Atomically increment the counter and publish the new value to SSE.
        TTL is initialised only if the key has none yet (prevents TTL reset).
        """
        new_count = int(
            await self.redis.eval(
                _LUA_INCR, 1, self._counter_key(request_id), quantity, _TTL_SECS
            )
        )
        await self.redis.publish(self._sse_channel(request_id), str(new_count))
        return new_count

    # ── atomic decrement (Lua) ────────────────────────────────────────────────

    async def decrement(self, request_id: UUID, quantity: int = 1) -> int:
        """
        Atomically decrement the counter (clamped at 0) and publish to SSE.
        TTL is initialised only if the key has none yet.
        """
        new_count = int(
            await self.redis.eval(
                _LUA_DECR, 1, self._counter_key(request_id), quantity, _TTL_SECS
            )
        )
        await self.redis.publish(self._sse_channel(request_id), str(new_count))
        return new_count

    # ── canonical DB→Redis sync ───────────────────────────────────────────────

    async def sync_counter_from_db(self, request_id: UUID) -> int:
        """
        Recompute the canonical wishlist count from Postgres, write it to
        Redis (with a 30-day TTL), and publish the corrected value on the SSE
        channel.

        Called after every wishlist write so DB and Redis never drift for long.
        Even if Redis had a stale value, the next write will self-heal it.
        """
        result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0)).where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status.in_(["waiting", "notified"]),
            )
        )
        db_count = int(result.scalar() or 0)

        await self.redis.set(self._counter_key(request_id), db_count, ex=_TTL_SECS)
        await self.redis.publish(self._sse_channel(request_id), str(db_count))

        logger.debug(
            "sync_counter_from_db request_id=%s db_count=%d", request_id, db_count
        )
        return db_count

    # ── check & trigger MoQ ───────────────────────────────────────────────────

    async def check_and_trigger(self, request_id: UUID) -> TriggerOutcome:
        """
        Check whether MoQ is reached and, if so, attempt the atomic
        active → moq_reached transition.

        Returns a TriggerOutcome with:
          threshold_met        – current_count >= offer.moq
          transition_performed – this call did the DB update (exactly once)
          status_after         – product status after the call
        """
        current_count = await self.get_current_count(request_id)

        product_result = await self.db.execute(
            select(ProductRequest).where(ProductRequest.id == request_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            return TriggerOutcome(
                threshold_met=False, transition_performed=False, status_after="unknown"
            )

        if product.status != "active":
            return TriggerOutcome(
                threshold_met=False,
                transition_performed=False,
                status_after=product.status,
            )

        offer_result = await self.db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_id,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()

        if not offer or not offer.moq or offer.moq <= 0:
            logger.warning(
                "check_and_trigger request_id=%s: no valid selected offer (moq=%s), skipping",
                request_id, getattr(offer, "moq", None),
            )
            return TriggerOutcome(
                threshold_met=False,
                transition_performed=False,
                status_after=product.status,
            )

        threshold_met = current_count >= offer.moq

        logger.info(
            "check_and_trigger request_id=%s current_count=%d target_moq=%d threshold_met=%s",
            request_id, current_count, offer.moq, threshold_met,
        )

        if not threshold_met:
            return TriggerOutcome(
                threshold_met=False,
                transition_performed=False,
                status_after=product.status,
            )

        transition_performed = await self.trigger_payment_phase(request_id, offer)
        status_after = "moq_reached" if transition_performed else product.status

        logger.info(
            "check_and_trigger request_id=%s transition_performed=%s status_after=%s",
            request_id, transition_performed, status_after,
        )
        return TriggerOutcome(
            threshold_met=True,
            transition_performed=transition_performed,
            status_after=status_after,
        )

    # ── trigger payment phase ─────────────────────────────────────────────────

    async def trigger_payment_phase(
        self, request_id: UUID, offer: SupplierOffer
    ) -> bool:
        """
        Atomically transition product active → moq_reached.

        The UPDATE uses 'WHERE status = active' as an optimistic-lock guard:
        if a concurrent worker already performed the transition, rowcount == 0
        and we return False without creating duplicate notifications or tasks.

        Returns True if this call performed the transition, False otherwise.
        """
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=48)

        # ── Atomic product status transition (guard: only from 'active') ──────
        updated = await self.db.execute(
            update(ProductRequest)
            .where(
                ProductRequest.id == request_id,
                ProductRequest.status == "active",  # ← optimistic-lock guard
            )
            .values(
                status="moq_reached",
                moq_reached_at=now,
                payment_deadline=deadline,
            )
            .returning(ProductRequest.id)
        )
        if updated.scalar_one_or_none() is None:
            # Another worker already transitioned – nothing left to do
            logger.info(
                "trigger_payment_phase request_id=%s skipped (already transitioned)",
                request_id,
            )
            return False

        # ── Transition all waiting → notified ─────────────────────────────────
        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "waiting",
            )
            .values(
                status="notified",
                notified_at=now,
                payment_deadline=deadline,
            )
        )
        await self.db.commit()

        # ── Create notification records (idempotent via ON CONFLICT DO NOTHING) ─
        notified_result = await self.db.execute(
            select(WishlistEntry.user_id).where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "notified",
            )
        )
        user_ids = [row[0] for row in notified_result.all()]

        if user_ids:
            notif_rows = [
                {
                    "user_id": uid,
                    "request_id": request_id,
                    "type": "moq_reached",
                    "channel": "email",
                    "subject": "Sipariş hazır! 48 saat içinde ödeme yapın",
                    "status": "pending",
                }
                for uid in user_ids
            ]
            notif_stmt = pg_insert(Notification.__table__).values(notif_rows)
            notif_stmt = notif_stmt.on_conflict_do_nothing(
                constraint="uq_notification_user_request_type"
            )
            await self.db.execute(notif_stmt)
            await self.db.commit()

        logger.info(
            "trigger_payment_phase request_id=%s deadline=%s users_notified=%d",
            request_id, deadline.isoformat(), len(user_ids),
        )

        # ── Dispatch Celery tasks ─────────────────────────────────────────────
        from app.tasks.email_tasks import send_moq_reached_email  # noqa: PLC0415
        from app.tasks.moq_tasks import cleanup_expired_entries  # noqa: PLC0415

        send_moq_reached_email.delay(str(request_id), deadline.isoformat())
        cleanup_expired_entries.apply_async(
            args=[str(request_id)],
            countdown=48 * 3600,
        )

        return True

    # ── post-48h cleanup ──────────────────────────────────────────────────────

    async def process_expired_entries(self, request_id: UUID) -> None:
        """
        Process entries after the 48-hour payment deadline.
        Called by the Celery cleanup task.
        """
        now = datetime.now(timezone.utc)

        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "notified",
                WishlistEntry.payment_deadline < now,
            )
            .values(status="expired")
        )
        await self.db.commit()

        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(WishlistEntry.quantity), 0)).where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "paid",
            )
        )
        paid_count = int(paid_result.scalar() or 0)

        offer_result = await self.db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_id,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()
        if not offer:
            return

        if paid_count >= offer.moq:
            await self._create_batch_order(request_id, offer, paid_count)
        else:
            await self._reset_to_active(request_id)

    # ── internal helpers ──────────────────────────────────────────────────────

    async def _create_batch_order(
        self, request_id: UUID, offer: SupplierOffer, quantity: int
    ) -> None:
        total_cost_usd = float(offer.unit_price_usd) * quantity
        if offer.shipping_cost_usd:
            total_cost_usd += float(offer.shipping_cost_usd)

        self.db.add(
            BatchOrder(
                request_id=request_id,
                offer_id=offer.id,
                total_quantity=quantity,
                total_cost_usd=Decimal(str(total_cost_usd)),
                status="pending",
            )
        )
        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(status="ordered")
        )
        await self.db.commit()

    async def _reset_to_active(self, request_id: UUID) -> None:
        await self.db.execute(
            update(WishlistEntry)
            .where(
                WishlistEntry.request_id == request_id,
                WishlistEntry.status == "expired",
            )
            .values(status="waiting", notified_at=None, payment_deadline=None)
        )
        await self.db.execute(
            update(ProductRequest)
            .where(ProductRequest.id == request_id)
            .values(status="active", moq_reached_at=None, payment_deadline=None)
        )
        await self.db.commit()
        # Re-sync Redis after resetting so the counter reflects the restored entries
        await self.sync_counter_from_db(request_id)
