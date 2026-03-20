"""
Backfill: supplier_offers.campaign_id from campaigns.selected_offer_id

One-time script to link existing SupplierOffer rows to their Campaign.
Run after deploying the migration that adds supplier_offers.campaign_id.

Usage:
    python -m scripts.backfill_offer_campaign_ids
"""
import asyncio
import os
import sys

# Ensure the backend package is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.models.models import Campaign, SupplierOffer


DATABASE_URL = os.environ.get("DATABASE_URL", "")
if "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.selected_offer_id.isnot(None))
        )
        updated = 0
        for campaign in result.scalars().all():
            res = await db.execute(
                update(SupplierOffer)
                .where(
                    SupplierOffer.id == campaign.selected_offer_id,
                    SupplierOffer.campaign_id.is_(None),
                )
                .values(campaign_id=campaign.id)
            )
            updated += res.rowcount

        await db.commit()
        print(f"Backfill complete: {updated} supplier_offers updated with campaign_id.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
