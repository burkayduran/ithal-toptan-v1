"""
Celery MoQ Tasks
Background jobs for MoQ cleanup and processing.
Primary source: campaigns table.
"""
from datetime import datetime, timezone
from sqlalchemy import select, and_
from uuid import UUID

import logging

from app.tasks.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.models.models import Campaign
from app.services.moq_service import MoQService
from app.tasks.email_tasks import send_moq_failed_email
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger("ithal_toptan")


@celery_app.task(name="app.tasks.moq_tasks.cleanup_expired_entries")
def cleanup_expired_entries(campaign_id: str):
    """
    Cleanup expired entries for a specific campaign.
    Called 48 hours after MoQ reached.

    Args:
        campaign_id: Campaign UUID
    """
    import asyncio
    asyncio.run(_cleanup_expired_entries_async(campaign_id))


async def _cleanup_expired_entries_async(campaign_id: str):
    """Async implementation of cleanup."""
    campaign_uuid = UUID(campaign_id)

    async with AsyncSessionLocal() as db:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

        try:
            moq_service = MoQService(db, redis_client)

            logger.info("Cleaning up expired entries for campaign %s", campaign_id)

            await moq_service.process_expired_entries(campaign_uuid)

            # Check result
            result = await db.execute(
                select(Campaign).where(Campaign.id == campaign_uuid)
            )
            campaign = result.scalar_one_or_none()

            if campaign:
                if campaign.status == "ordered":
                    logger.info("MoQ success! Campaign %s ordered", campaign_id)
                elif campaign.status == "active":
                    logger.info("MoQ failed! Campaign %s reset to active", campaign_id)
                    send_moq_failed_email.delay(str(campaign_id))

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

        # Find campaigns with expired deadline
        result = await db.execute(
            select(Campaign).where(
                and_(
                    Campaign.status == "moq_reached",
                    Campaign.payment_deadline.isnot(None),
                    Campaign.payment_deadline < now
                )
            )
        )
        expired_campaigns = result.scalars().all()

        if not expired_campaigns:
            logger.info("No expired campaigns to cleanup")
            return

        logger.info("Found %d expired campaigns. Cleaning up...", len(expired_campaigns))

        for campaign in expired_campaigns:
            cleanup_expired_entries.delay(str(campaign.id))

        logger.info("Scheduled cleanup for %d campaigns", len(expired_campaigns))
