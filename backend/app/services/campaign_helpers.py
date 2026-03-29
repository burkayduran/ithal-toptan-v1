"""
Campaign domain helpers — pure DB queries, no Redis dependency.
Used by admin endpoints and anywhere an authoritative count is needed.
"""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.models import CampaignParticipant


async def get_db_participant_count(db: AsyncSession, campaign_id: UUID) -> int:
    """Return authoritative participant count directly from DB.

    Counts sum(quantity) for participants with status in
    ('joined', 'invited') — the canonical active states.
    Does NOT use the Redis cache so the result is always current.
    """
    result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
        .where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
    )
    return int(result.scalar() or 0)


async def is_moq_reached(db: AsyncSession, campaign_id: UUID, moq: int) -> tuple[int, bool]:
    """Return (current_count, reached) using the authoritative DB count.

    Args:
        db: async DB session
        campaign_id: UUID of the campaign
        moq: minimum order quantity threshold

    Returns:
        (current_count, True) if count >= moq, else (current_count, False)
    """
    count = await get_db_participant_count(db, campaign_id)
    return count, count >= moq
