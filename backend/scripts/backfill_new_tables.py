"""
One-time backfill: migrate data from legacy tables to new domain tables.

Usage:
  docker compose exec api python scripts/backfill_new_tables.py

  OR with --dry-run flag to preview without writing:
  docker compose exec api python scripts/backfill_new_tables.py --dry-run
"""
import asyncio
import sys
import logging
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Setup path
sys.path.insert(0, "/app")

from app.db.session import AsyncSessionLocal
from app.models.models import (
    # Legacy
    ProductRequest, SupplierOffer, WishlistEntry, Payment, BatchOrder,
    # New domain
    Product, Supplier, ProductSuggestion, Campaign,
    CampaignParticipant, PaymentTransaction, ProcurementOrder,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("backfill")

DRY_RUN = "--dry-run" in sys.argv

# Status'ler: hangisi suggestion, hangisi campaign?
SUGGESTION_STATUSES = {"pending", "reviewing", "approved", "rejected"}
CAMPAIGN_STATUSES = {"draft", "active", "moq_reached", "payment_collecting", "ordered", "delivered", "cancelled"}

WISHLIST_STATUS_MAP = {
    "waiting": "joined",
    "notified": "invited",
    "paid": "paid",
    "expired": "expired",
    "cancelled": "cancelled",
}


async def backfill_suppliers(db: AsyncSession) -> dict[str, UUID]:
    """
    supplier_offers.supplier_name → suppliers tablosu.
    Aynı isimli tedarikçileri tek kayıta indirir.
    Returns: {supplier_name_lower: supplier_id} mapping.
    """
    logger.info("=== Backfill: suppliers ===")

    result = await db.execute(
        select(
            SupplierOffer.supplier_name,
            SupplierOffer.supplier_country,
        )
        .where(SupplierOffer.supplier_name.isnot(None))
        .distinct(SupplierOffer.supplier_name)
    )
    rows = result.all()

    supplier_map: dict[str, UUID] = {}
    created = 0

    for name, country in rows:
        if not name or not name.strip():
            continue
        key = name.strip().lower()
        if key in supplier_map:
            continue

        # Zaten var mı kontrol et
        existing = await db.execute(
            select(Supplier).where(func.lower(Supplier.name) == key)
        )
        existing_supplier = existing.scalar_one_or_none()

        if existing_supplier:
            supplier_map[key] = existing_supplier.id
            continue

        supplier = Supplier(
            name=name.strip(),
            country=country or "CN",
        )
        if not DRY_RUN:
            db.add(supplier)
            await db.flush()
            supplier_map[key] = supplier.id
        else:
            supplier_map[key] = UUID("00000000-0000-0000-0000-000000000000")
        created += 1

    logger.info(f"  Suppliers: {created} created, {len(supplier_map)} total unique")
    return supplier_map


async def backfill_products_and_campaigns(
    db: AsyncSession,
    supplier_map: dict[str, UUID],
) -> dict[UUID, UUID]:
    """
    product_requests (campaign statuses) → products + campaigns.
    Returns: {old_request_id: new_campaign_id} mapping.
    """
    logger.info("=== Backfill: products + campaigns ===")

    result = await db.execute(
        select(ProductRequest)
        .where(ProductRequest.status.in_(CAMPAIGN_STATUSES))
        .order_by(ProductRequest.created_at)
    )
    requests = result.scalars().all()

    campaign_map: dict[UUID, UUID] = {}
    products_created = 0
    campaigns_created = 0

    for req in requests:
        # Zaten backfill edilmiş mi?
        existing_campaign = await db.execute(
            select(Campaign).where(Campaign.legacy_request_id == req.id)
        )
        if existing_campaign.scalar_one_or_none():
            # Still populate mapping for participant backfill
            camp = (await db.execute(
                select(Campaign).where(Campaign.legacy_request_id == req.id)
            )).scalar_one()
            campaign_map[req.id] = camp.id
            logger.debug(f"  Skip {req.id} — already backfilled")
            continue

        # 1. Product oluştur
        product = Product(
            title=req.title,
            description=req.description,
            category_id=req.category_id,
            images=req.images or [],
            created_by=req.created_by,
            legacy_request_id=req.id,
        )

        if not DRY_RUN:
            db.add(product)
            await db.flush()

        products_created += 1

        # 2. Selected offer'ı bul
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == req.id,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()

        # 3. Campaign oluştur (snapshot alanları offer'dan doldurulur)
        campaign = Campaign(
            product_id=product.id if not DRY_RUN else UUID("00000000-0000-0000-0000-000000000000"),
            selected_offer_id=offer.id if offer else None,
            status=req.status,

            # Snapshot alanları
            supplier_name_snapshot=offer.supplier_name if offer else None,
            supplier_country_snapshot=offer.supplier_country if offer else None,
            unit_price_usd_snapshot=float(offer.unit_price_usd) if offer and offer.unit_price_usd else None,
            shipping_cost_usd_snapshot=float(offer.shipping_cost_usd) if offer and offer.shipping_cost_usd else None,
            customs_rate_snapshot=float(offer.customs_rate) if offer and offer.customs_rate else None,
            margin_rate_snapshot=float(offer.margin_rate) if offer and offer.margin_rate else None,
            fx_rate_snapshot=float(offer.usd_rate_used) if offer and offer.usd_rate_used else None,
            selling_price_try_snapshot=float(offer.selling_price_try) if offer and offer.selling_price_try else None,

            moq=offer.moq if offer else 0,
            lead_time_days=offer.lead_time_days if offer else None,
            view_count=req.view_count,
            legacy_request_id=req.id,
            created_by=req.created_by,
            created_at=req.created_at,
            activated_at=req.activated_at,
            moq_reached_at=req.moq_reached_at,
            payment_deadline=req.payment_deadline,
        )

        if not DRY_RUN:
            db.add(campaign)
            await db.flush()
            campaign_map[req.id] = campaign.id

        campaigns_created += 1

    logger.info(f"  Products: {products_created}, Campaigns: {campaigns_created}")
    return campaign_map


async def backfill_suggestions(db: AsyncSession):
    """product_requests (suggestion statuses) → product_suggestions."""
    logger.info("=== Backfill: product_suggestions ===")

    result = await db.execute(
        select(ProductRequest)
        .where(ProductRequest.status.in_(SUGGESTION_STATUSES))
        .order_by(ProductRequest.created_at)
    )
    requests = result.scalars().all()
    created = 0

    for req in requests:
        # Zaten var mı?
        existing = await db.execute(
            select(ProductSuggestion).where(
                ProductSuggestion.created_by == req.created_by,
                ProductSuggestion.title == req.title,
            )
        )
        if existing.scalar_one_or_none():
            continue

        suggestion = ProductSuggestion(
            title=req.title,
            description=req.description,
            category_id=req.category_id,
            reference_url=req.reference_url,
            images=req.images or [],
            expected_price_try=float(req.expected_price_try) if req.expected_price_try else None,
            status=req.status,
            admin_notes=req.admin_notes,
            created_by=req.created_by,
            created_at=req.created_at,
        )

        if not DRY_RUN:
            db.add(suggestion)
        created += 1

    logger.info(f"  Suggestions: {created} created")


async def backfill_participants(
    db: AsyncSession,
    campaign_map: dict[UUID, UUID],
):
    """wishlist_entries → campaign_participants."""
    logger.info("=== Backfill: campaign_participants ===")

    result = await db.execute(
        select(WishlistEntry).order_by(WishlistEntry.joined_at)
    )
    entries = result.scalars().all()
    created = 0
    skipped = 0

    for entry in entries:
        campaign_id = campaign_map.get(entry.request_id)
        if not campaign_id:
            skipped += 1
            continue

        # Zaten var mı?
        existing = await db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.legacy_entry_id == entry.id
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Selling price snapshot — offer'dan al
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == entry.request_id,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()
        selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else None

        participant = CampaignParticipant(
            campaign_id=campaign_id,
            user_id=entry.user_id,
            quantity=entry.quantity,
            status=WISHLIST_STATUS_MAP.get(entry.status, "joined"),
            unit_price_try_snapshot=selling_price,
            total_amount_try_snapshot=round(entry.quantity * selling_price, 2) if selling_price else None,
            legacy_entry_id=entry.id,
            joined_at=entry.joined_at,
            invited_at=entry.notified_at,
            payment_deadline=entry.payment_deadline,
            paid_at=entry.paid_at,
        )

        if not DRY_RUN:
            db.add(participant)
            await db.flush()
        created += 1

    logger.info(f"  Participants: {created} created, {skipped} skipped (no matching campaign)")


async def backfill_payment_transactions(
    db: AsyncSession,
    campaign_map: dict[UUID, UUID],
):
    """payments → payment_transactions."""
    logger.info("=== Backfill: payment_transactions ===")

    result = await db.execute(select(Payment).order_by(Payment.created_at))
    payments = result.scalars().all()
    created = 0
    skipped = 0

    for pay in payments:
        campaign_id = campaign_map.get(pay.request_id)
        if not campaign_id:
            skipped += 1
            continue

        # Participant'ı bul
        participant_result = await db.execute(
            select(CampaignParticipant).where(
                CampaignParticipant.legacy_entry_id == pay.wishlist_entry_id
            )
        )
        participant = participant_result.scalar_one_or_none()
        if not participant:
            skipped += 1
            continue

        # Zaten var mı?
        existing = await db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.legacy_payment_id == pay.id
            )
        )
        if existing.scalar_one_or_none():
            continue

        # Offer'dan fiyat snapshot
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == pay.request_id,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()

        tx = PaymentTransaction(
            participant_id=participant.id,
            campaign_id=campaign_id,
            user_id=pay.user_id,
            amount_try=float(pay.amount_try),
            quantity=pay.quantity,
            unit_price_try_snapshot=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
            fx_rate_snapshot=float(offer.usd_rate_used) if offer and offer.usd_rate_used else None,
            provider="iyzico",
            provider_payment_id=pay.iyzico_payment_id,
            provider_token=pay.iyzico_token,
            provider_conversation_id=pay.iyzico_conversation_id,
            status=pay.status,
            failure_reason=pay.failure_reason,
            legacy_payment_id=pay.id,
            created_at=pay.created_at,
            completed_at=pay.paid_at,
        )

        if not DRY_RUN:
            db.add(tx)
        created += 1

    logger.info(f"  Transactions: {created} created, {skipped} skipped")


async def backfill_procurement_orders(
    db: AsyncSession,
    campaign_map: dict[UUID, UUID],
):
    """batch_orders → procurement_orders."""
    logger.info("=== Backfill: procurement_orders ===")

    result = await db.execute(select(BatchOrder).order_by(BatchOrder.created_at))
    orders = result.scalars().all()
    created = 0
    skipped = 0

    for bo in orders:
        campaign_id = campaign_map.get(bo.request_id)
        if not campaign_id:
            skipped += 1
            continue

        existing = await db.execute(
            select(ProcurementOrder).where(
                ProcurementOrder.legacy_batch_order_id == bo.id
            )
        )
        if existing.scalar_one_or_none():
            continue

        po = ProcurementOrder(
            campaign_id=campaign_id,
            offer_id=bo.offer_id,
            total_quantity=bo.total_quantity,
            total_cost_usd=float(bo.total_cost_usd) if bo.total_cost_usd else None,
            payment_total_try=float(bo.payment_total_try) if bo.payment_total_try else None,
            status=bo.status,
            supplier_order_ref=bo.supplier_order_ref,
            tracking_number=bo.tracking_number,
            legacy_batch_order_id=bo.id,
            created_at=bo.created_at,
            delivered_at=bo.delivered_at,
        )

        if not DRY_RUN:
            db.add(po)
        created += 1

    logger.info(f"  Procurement orders: {created} created, {skipped} skipped")


async def main():
    logger.info(f"{'[DRY RUN] ' if DRY_RUN else ''}Starting backfill...")

    async with AsyncSessionLocal() as db:
        try:
            supplier_map = await backfill_suppliers(db)
            campaign_map = await backfill_products_and_campaigns(db, supplier_map)
            await backfill_suggestions(db)
            await backfill_participants(db, campaign_map)
            await backfill_payment_transactions(db, campaign_map)
            await backfill_procurement_orders(db, campaign_map)

            if not DRY_RUN:
                await db.commit()
                logger.info("Backfill committed successfully")
            else:
                await db.rollback()
                logger.info("Dry run complete — no changes made")

        except Exception as e:
            await db.rollback()
            logger.error(f"Backfill failed: {e}", exc_info=True)
            raise


if __name__ == "__main__":
    asyncio.run(main())
