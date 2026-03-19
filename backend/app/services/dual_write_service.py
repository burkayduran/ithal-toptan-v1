"""
Dual-write service — shadow writes to new domain tables.
Fire-and-forget safe: errors are logged, never rollback legacy.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Product, Campaign, ProductSuggestion, CampaignParticipant,
    PaymentTransaction, SupplierOffer, CampaignStatusHistory,
    ParticipantStatusHistory,
)

logger = logging.getLogger("dual_write")


class DualWriteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── D1: Admin create_product → Product + Campaign(draft) ──────────────
    async def shadow_create_product(
        self,
        legacy_request_id: UUID,
        title: str,
        description: str | None,
        category_id: UUID | None,
        images: list[str],
        created_by: UUID | None,
        offer: SupplierOffer | None = None,
    ) -> None:
        try:
            product = Product(
                title=title,
                description=description,
                category_id=category_id,
                images=images or [],
                created_by=created_by,
                legacy_request_id=legacy_request_id,
            )
            self.db.add(product)
            await self.db.flush()

            campaign = Campaign(
                product_id=product.id,
                selected_offer_id=offer.id if offer else None,
                status="draft",
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
                legacy_request_id=legacy_request_id,
                created_by=created_by,
            )
            self.db.add(campaign)
        except Exception:
            logger.exception("shadow_create_product failed for %s", legacy_request_id)

    # ── D2: Admin publish_product → Campaign status draft→active ──────────
    async def shadow_publish(
        self,
        legacy_request_id: UUID,
        activated_at: datetime | None = None,
    ) -> None:
        try:
            result = await self.db.execute(
                select(Campaign).where(Campaign.legacy_request_id == legacy_request_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                logger.warning("shadow_publish: no campaign for legacy %s", legacy_request_id)
                return

            old_status = campaign.status
            campaign.status = "active"
            campaign.activated_at = activated_at or datetime.now(timezone.utc)

            self.db.add(CampaignStatusHistory(
                campaign_id=campaign.id,
                old_status=old_status,
                new_status="active",
                reason="admin_publish",
            ))
        except Exception:
            logger.exception("shadow_publish failed for %s", legacy_request_id)

    # ── D3: Admin update_product → Campaign snapshot güncelle ─────────────
    async def shadow_update_product(
        self,
        legacy_request_id: UUID,
        offer: SupplierOffer | None = None,
        title: str | None = None,
        description: str | None = None,
        images: list[str] | None = None,
    ) -> None:
        try:
            result = await self.db.execute(
                select(Campaign).where(Campaign.legacy_request_id == legacy_request_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                return

            if title is not None:
                campaign.title_override = title
            if description is not None:
                campaign.description_override = description
            if images is not None:
                campaign.images_override = images

            if offer:
                campaign.selected_offer_id = offer.id
                campaign.supplier_name_snapshot = offer.supplier_name
                campaign.supplier_country_snapshot = offer.supplier_country
                campaign.unit_price_usd_snapshot = float(offer.unit_price_usd) if offer.unit_price_usd else None
                campaign.shipping_cost_usd_snapshot = float(offer.shipping_cost_usd) if offer.shipping_cost_usd else None
                campaign.customs_rate_snapshot = float(offer.customs_rate) if offer.customs_rate else None
                campaign.margin_rate_snapshot = float(offer.margin_rate) if offer.margin_rate else None
                campaign.fx_rate_snapshot = float(offer.usd_rate_used) if offer.usd_rate_used else None
                campaign.selling_price_try_snapshot = float(offer.selling_price_try) if offer.selling_price_try else None
                campaign.moq = offer.moq if offer.moq else campaign.moq
                campaign.lead_time_days = offer.lead_time_days
        except Exception:
            logger.exception("shadow_update_product failed for %s", legacy_request_id)

    # ── D4: User product request → ProductSuggestion ──────────────────────
    async def shadow_create_suggestion(
        self,
        title: str,
        description: str | None,
        category_id: UUID | None,
        reference_url: str | None,
        expected_price_try: float | None,
        created_by: UUID,
    ) -> None:
        try:
            suggestion = ProductSuggestion(
                title=title,
                description=description,
                category_id=category_id,
                reference_url=reference_url,
                expected_price_try=expected_price_try,
                status="pending",
                created_by=created_by,
            )
            self.db.add(suggestion)
        except Exception:
            logger.exception("shadow_create_suggestion failed")

    # ── D5: Wishlist join → CampaignParticipant ───────────────────────────
    async def shadow_join_wishlist(
        self,
        legacy_request_id: UUID,
        legacy_entry_id: UUID,
        user_id: UUID,
        quantity: int,
        status: str,
        selling_price_try: float | None = None,
    ) -> None:
        try:
            result = await self.db.execute(
                select(Campaign).where(Campaign.legacy_request_id == legacy_request_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                logger.warning("shadow_join_wishlist: no campaign for legacy %s", legacy_request_id)
                return

            # Zaten var mı?
            existing = await self.db.execute(
                select(CampaignParticipant).where(
                    CampaignParticipant.campaign_id == campaign.id,
                    CampaignParticipant.user_id == user_id,
                )
            )
            participant = existing.scalar_one_or_none()
            if participant:
                participant.quantity = quantity
                return

            status_map = {
                "waiting": "joined",
                "notified": "invited",
                "paid": "paid",
                "expired": "expired",
                "cancelled": "cancelled",
            }

            participant = CampaignParticipant(
                campaign_id=campaign.id,
                user_id=user_id,
                quantity=quantity,
                status=status_map.get(status, "joined"),
                unit_price_try_snapshot=selling_price_try,
                total_amount_try_snapshot=round(quantity * selling_price_try, 2) if selling_price_try else None,
                legacy_entry_id=legacy_entry_id,
            )
            self.db.add(participant)
        except Exception:
            logger.exception("shadow_join_wishlist failed for entry %s", legacy_entry_id)

    # ── D6: MoQ reached → Campaign status active→moq_reached ─────────────
    async def shadow_moq_reached(
        self,
        legacy_request_id: UUID,
        moq_reached_at: datetime | None = None,
        payment_deadline: datetime | None = None,
    ) -> None:
        try:
            result = await self.db.execute(
                select(Campaign).where(Campaign.legacy_request_id == legacy_request_id)
            )
            campaign = result.scalar_one_or_none()
            if not campaign:
                return

            old_status = campaign.status
            campaign.status = "moq_reached"
            campaign.moq_reached_at = moq_reached_at
            campaign.payment_deadline = payment_deadline

            self.db.add(CampaignStatusHistory(
                campaign_id=campaign.id,
                old_status=old_status,
                new_status="moq_reached",
                reason="moq_threshold_reached",
            ))

            # Participant'ları da güncelle: joined → invited
            from sqlalchemy import update as sa_update
            await self.db.execute(
                sa_update(CampaignParticipant)
                .where(
                    CampaignParticipant.campaign_id == campaign.id,
                    CampaignParticipant.status == "joined",
                )
                .values(
                    status="invited",
                    invited_at=moq_reached_at,
                    payment_deadline=payment_deadline,
                )
            )
        except Exception:
            logger.exception("shadow_moq_reached failed for %s", legacy_request_id)

    # ── D7: Payment confirm → PaymentTransaction + Participant status ─────
    async def shadow_confirm_payment(
        self,
        legacy_entry_id: UUID,
        legacy_payment_id: UUID,
        legacy_request_id: UUID,
        user_id: UUID,
        amount_try: float,
        quantity: int,
        offer: SupplierOffer | None = None,
    ) -> None:
        try:
            # Participant'ı bul
            result = await self.db.execute(
                select(CampaignParticipant).where(
                    CampaignParticipant.legacy_entry_id == legacy_entry_id
                )
            )
            participant = result.scalar_one_or_none()
            if not participant:
                logger.warning("shadow_confirm_payment: no participant for entry %s", legacy_entry_id)
                return

            old_status = participant.status
            participant.status = "paid"
            participant.paid_at = datetime.now(timezone.utc)

            self.db.add(ParticipantStatusHistory(
                participant_id=participant.id,
                old_status=old_status,
                new_status="paid",
                reason="payment_confirmed",
            ))

            # Campaign'ı bul
            campaign_result = await self.db.execute(
                select(Campaign).where(Campaign.legacy_request_id == legacy_request_id)
            )
            campaign = campaign_result.scalar_one_or_none()

            tx = PaymentTransaction(
                participant_id=participant.id,
                campaign_id=participant.campaign_id,
                user_id=user_id,
                amount_try=amount_try,
                quantity=quantity,
                unit_price_try_snapshot=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
                fx_rate_snapshot=float(offer.usd_rate_used) if offer and offer.usd_rate_used else None,
                provider="iyzico",
                status="success",
                legacy_payment_id=legacy_payment_id,
                completed_at=datetime.now(timezone.utc),
            )
            self.db.add(tx)
        except Exception:
            logger.exception("shadow_confirm_payment failed for entry %s", legacy_entry_id)
