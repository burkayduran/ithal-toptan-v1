"""
MoQ (Minimum Order Quantity) Service
Redis-based atomic counter and trigger logic.
Primary source: campaigns + campaign_participants tables.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update

from app.models.models import (
    Campaign, CampaignParticipant, CampaignStatusHistory,
    Notification,
)


class MoQService:
    """Handle MoQ tracking and payment phase triggering."""

    def __init__(self, db: AsyncSession, redis_client: aioredis.Redis):
        self.db = db
        self.redis = redis_client

    def _get_counter_key(self, campaign_id: UUID) -> str:
        """Get Redis key for MoQ counter."""
        return f"moq:count:{campaign_id}"

    async def get_current_count(self, campaign_id: UUID) -> int:
        """Get current participant count from Redis (with DB fallback)."""
        count = await self.redis.get(self._get_counter_key(campaign_id))

        if count is not None:
            return int(count)

        result = await self.db.execute(
            select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status.in_(["joined", "invited"])
            )
        )
        db_count = int(result.scalar() or 0)

        await self.redis.set(self._get_counter_key(campaign_id), db_count, ex=30 * 24 * 3600)
        return db_count

    async def increment(self, campaign_id: UUID, quantity: int = 1) -> int:
        """Increment MoQ counter atomically with TTL bootstrap via Lua."""
        key = self._get_counter_key(campaign_id)
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

        await self.redis.publish(f"moq:progress:{campaign_id}", str(new_count))
        return new_count

    async def decrement(self, campaign_id: UUID, quantity: int = 1) -> int:
        """Decrement MoQ counter atomically with Lua and floor at zero."""
        key = self._get_counter_key(campaign_id)
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
        await self.redis.publish(f"moq:progress:{campaign_id}", str(new_count))
        return new_count

    async def sync_counter_from_db(self, campaign_id: UUID) -> int:
        """Force-sync Redis counter from DB aggregate to avoid drift under concurrent updates."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status.in_(["joined", "invited"])
            )
        )
        db_count = int(result.scalar() or 0)
        await self.redis.set(self._get_counter_key(campaign_id), db_count, ex=30 * 24 * 3600)
        await self.redis.publish(f"moq:progress:{campaign_id}", str(db_count))
        return db_count

    async def check_and_trigger(self, campaign_id: UUID) -> dict:
        """Check threshold and attempt atomic payment-phase transition."""
        current_count = await self.get_current_count(campaign_id)

        result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()

        if not campaign or campaign.status != "active":
            return {"threshold_met": False, "transition_performed": False, "status_after": campaign.status if campaign else "missing"}

        if not campaign.moq or campaign.moq <= 0 or current_count < campaign.moq:
            return {"threshold_met": False, "transition_performed": False, "status_after": campaign.status}

        transition_performed = await self.trigger_payment_phase(campaign_id, campaign)

        refreshed = await self.db.execute(select(Campaign.status).where(Campaign.id == campaign_id))
        status_after = refreshed.scalar_one_or_none() or campaign.status
        return {"threshold_met": True, "transition_performed": transition_performed, "status_after": status_after}

    async def trigger_payment_phase(self, campaign_id: UUID, campaign: Campaign) -> bool:
        """Trigger 48-hour payment window when MoQ is reached.
        All DB mutations happen in a single transaction to avoid partial state."""
        now = datetime.now(timezone.utc)
        deadline = now + timedelta(hours=48)

        # Campaign status: active → moq_reached
        campaign_update = await self.db.execute(
            update(Campaign)
            .where(
                Campaign.id == campaign_id,
                Campaign.status == "active"
            )
            .values(
                status="moq_reached",
                moq_reached_at=now,
                payment_deadline=deadline
            )
        )

        if campaign_update.rowcount == 0:
            await self.db.rollback()
            return False

        # Participants: joined → invited
        await self.db.execute(
            update(CampaignParticipant)
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status == "joined"
            )
            .values(
                status="invited",
                invited_at=now,
                payment_deadline=deadline
            )
        )

        # Status history
        self.db.add(CampaignStatusHistory(
            campaign_id=campaign_id,
            old_status="active",
            new_status="moq_reached",
            reason="MOQ threshold reached",
        ))

        # Notifications
        invited_result = await self.db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status == "invited"
            )
        )

        existing_notif_result = await self.db.execute(
            select(Notification.user_id).where(
                Notification.campaign_id == campaign_id,
                Notification.type == "moq_reached",
                Notification.channel == "email",
                Notification.status.in_(["pending", "sent", "delivered", "opened", "clicked"]),
            )
        )
        existing_user_ids = {row[0] for row in existing_notif_result.all()}

        for participant in invited_result.scalars().all():
            if participant.user_id in existing_user_ids:
                continue
            self.db.add(
                Notification(
                    user_id=participant.user_id,
                    campaign_id=campaign_id,
                    request_id=campaign.legacy_request_id,
                    type="moq_reached",
                    channel="email",
                    subject="Sipariş hazır! 48 saat içinde ödeme yapın",
                    status="pending"
                )
            )

        # TEK COMMIT — status + participants + notification hepsi atomik
        await self.db.commit()

        # Side effects (Celery tasks) commit sonrası
        from app.tasks.email_tasks import send_moq_reached_email
        from app.tasks.moq_tasks import cleanup_expired_entries

        send_moq_reached_email.delay(str(campaign_id), deadline.isoformat())
        cleanup_expired_entries.apply_async(args=[str(campaign_id)], countdown=48 * 3600)

        return True

    async def process_expired_entries(self, campaign_id: UUID):
        """Process entries after 48-hour deadline."""
        now = datetime.now(timezone.utc)

        # Transition campaign moq_reached → payment_collecting
        await self.db.execute(
            update(Campaign)
            .where(
                Campaign.id == campaign_id,
                Campaign.status == "moq_reached",
            )
            .values(status="payment_collecting")
        )

        # Expire unpaid participants
        await self.db.execute(
            update(CampaignParticipant)
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status == "invited",
                CampaignParticipant.payment_deadline < now
            )
            .values(status="expired")
        )

        await self.db.commit()

        # Check paid count
        paid_result = await self.db.execute(
            select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status == "paid"
            )
        )
        paid_count = int(paid_result.scalar() or 0)

        campaign_result = await self.db.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if not campaign:
            return

        if paid_count >= campaign.moq:
            await self._create_procurement_order(campaign_id, campaign, paid_count)
        else:
            await self._reset_to_active(campaign_id)

    async def _create_procurement_order(self, campaign_id: UUID, campaign: Campaign, quantity: int):
        from app.models.models import ProcurementOrder

        total_cost_usd = float(campaign.unit_price_usd_snapshot or 0) * quantity + float(campaign.shipping_cost_usd_snapshot or 0)

        order = ProcurementOrder(
            campaign_id=campaign_id,
            offer_id=campaign.selected_offer_id,
            total_quantity=quantity,
            total_cost_usd=total_cost_usd,
            fx_rate_at_order=float(campaign.fx_rate_snapshot) if campaign.fx_rate_snapshot else None,
            status="pending",
        )
        self.db.add(order)

        now = datetime.now(timezone.utc)
        await self.db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id, Campaign.status == "payment_collecting")
            .values(status="ordered", ordered_at=now)
        )

        self.db.add(CampaignStatusHistory(
            campaign_id=campaign_id,
            old_status="payment_collecting",
            new_status="ordered",
            reason="Sufficient payments collected",
        ))

        await self.db.commit()

    async def _reset_to_active(self, campaign_id: UUID):
        await self.db.execute(
            update(CampaignParticipant)
            .where(
                CampaignParticipant.campaign_id == campaign_id,
                CampaignParticipant.status == "expired"
            )
            .values(
                status="joined",
                invited_at=None,
                payment_deadline=None
            )
        )

        await self.db.execute(
            update(Campaign)
            .where(
                Campaign.id == campaign_id,
                Campaign.status == "payment_collecting",
            )
            .values(
                status="active",
                moq_reached_at=None,
                payment_deadline=None
            )
        )

        self.db.add(CampaignStatusHistory(
            campaign_id=campaign_id,
            old_status="payment_collecting",
            new_status="active",
            reason="Insufficient payments, reset",
        ))

        await self.db.commit()

        current = await self.get_current_count(campaign_id)
        await self.redis.set(self._get_counter_key(campaign_id), current, ex=30 * 24 * 3600)
