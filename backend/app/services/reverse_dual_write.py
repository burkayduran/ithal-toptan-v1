"""
Reverse dual-write service — shadow writes from NEW tables back to LEGACY tables.
V2 endpoint'leri yeni tablolara yazarken eski tablolara da shadow yazar.
Faz 4 sonrası kaldırılacak.

Fire-and-forget safe: errors are logged, never rollback primary write.
"""
import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update as sa_update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ProductRequest, SupplierOffer, WishlistEntry, Payment,
    Campaign, Product, CampaignParticipant, ProductSuggestion,
)

logger = logging.getLogger("reverse_dual_write")

# New → Legacy status mapping
_STATUS_MAP = {
    "joined": "waiting",
    "invited": "notified",
    "paid": "paid",
    "expired": "expired",
    "cancelled": "cancelled",
}

# Campaign → ProductRequest status mapping
_CAMPAIGN_STATUS_MAP = {
    "draft": "draft",
    "active": "active",
    "moq_reached": "moq_reached",
    "payment_collecting": "payment_collecting",
    "ordered": "ordered",
    "delivered": "delivered",
    "cancelled": "cancelled",
}


class ReverseDualWrite:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def shadow_create_campaign(
        self,
        campaign: Campaign,
        product: Product,
        offer: SupplierOffer,
        admin_id: UUID | None,
    ) -> None:
        """Create legacy ProductRequest + link SupplierOffer.request_id."""
        try:
            legacy_pr = ProductRequest(
                title=product.title,
                description=product.description,
                category_id=product.category_id,
                images=product.images or [],
                status="draft",
                created_by=admin_id,
            )
            self.db.add(legacy_pr)
            await self.db.flush()

            # Link SupplierOffer to legacy ProductRequest
            offer.request_id = legacy_pr.id

            # Set legacy references
            campaign.legacy_request_id = legacy_pr.id
            product.legacy_request_id = legacy_pr.id
        except Exception:
            logger.exception("shadow_create_campaign failed for campaign %s", campaign.id)

    async def shadow_publish_campaign(self, campaign: Campaign) -> None:
        """Legacy ProductRequest.status = 'active'."""
        try:
            if not campaign.legacy_request_id:
                return
            result = await self.db.execute(
                select(ProductRequest).where(ProductRequest.id == campaign.legacy_request_id)
            )
            pr = result.scalar_one_or_none()
            if not pr:
                return
            pr.status = "active"
            pr.activated_at = campaign.activated_at or datetime.now(timezone.utc)
        except Exception:
            logger.exception("shadow_publish_campaign failed for campaign %s", campaign.id)

    async def shadow_update_campaign(self, campaign: Campaign, product: Product) -> None:
        """Legacy ProductRequest field updates."""
        try:
            if not campaign.legacy_request_id:
                return
            result = await self.db.execute(
                select(ProductRequest).where(ProductRequest.id == campaign.legacy_request_id)
            )
            pr = result.scalar_one_or_none()
            if not pr:
                return

            # Sync product fields
            title = campaign.title_override or product.title
            desc = campaign.description_override or product.description
            images = campaign.images_override or product.images

            pr.title = title
            pr.description = desc
            pr.images = images or []
            pr.category_id = product.category_id
        except Exception:
            logger.exception("shadow_update_campaign failed for campaign %s", campaign.id)

    async def shadow_join_campaign(
        self,
        participant: CampaignParticipant,
        campaign: Campaign,
    ) -> None:
        """Legacy WishlistEntry upsert. Sets participant.legacy_entry_id."""
        try:
            if not campaign.legacy_request_id:
                return

            legacy_status = _STATUS_MAP.get(participant.status, "waiting")

            upsert_stmt = (
                pg_insert(WishlistEntry)
                .values(
                    request_id=campaign.legacy_request_id,
                    user_id=participant.user_id,
                    quantity=participant.quantity,
                    status=legacy_status,
                )
                .on_conflict_do_update(
                    index_elements=[WishlistEntry.request_id, WishlistEntry.user_id],
                    set_={"quantity": participant.quantity},
                )
                .returning(WishlistEntry.id)
            )
            result = await self.db.execute(upsert_stmt)
            entry_id = result.scalar_one_or_none()
            if entry_id:
                participant.legacy_entry_id = entry_id
        except Exception:
            logger.exception("shadow_join_campaign failed for participant %s", participant.id)

    async def shadow_campaign_status(
        self,
        campaign: Campaign,
        new_status: str,
    ) -> None:
        """Legacy ProductRequest.status update."""
        try:
            if not campaign.legacy_request_id:
                return

            legacy_status = _CAMPAIGN_STATUS_MAP.get(new_status, new_status)
            values: dict = {"status": legacy_status}

            if new_status == "moq_reached":
                values["moq_reached_at"] = campaign.moq_reached_at
                values["payment_deadline"] = campaign.payment_deadline

            await self.db.execute(
                sa_update(ProductRequest)
                .where(ProductRequest.id == campaign.legacy_request_id)
                .values(**values)
            )
        except Exception:
            logger.exception("shadow_campaign_status failed for campaign %s", campaign.id)

    async def shadow_participants_invited(
        self,
        campaign: Campaign,
        deadline: datetime,
    ) -> None:
        """Legacy WishlistEntry waiting → notified."""
        try:
            if not campaign.legacy_request_id:
                return

            await self.db.execute(
                sa_update(WishlistEntry)
                .where(
                    WishlistEntry.request_id == campaign.legacy_request_id,
                    WishlistEntry.status == "waiting",
                )
                .values(
                    status="notified",
                    notified_at=campaign.moq_reached_at or datetime.now(timezone.utc),
                    payment_deadline=deadline,
                )
            )
        except Exception:
            logger.exception("shadow_participants_invited failed for campaign %s", campaign.id)

    async def shadow_payment_confirm(
        self,
        participant: CampaignParticipant,
        campaign: Campaign,
        amount_try: float,
        paid_at: datetime,
    ) -> None:
        """Legacy WishlistEntry.status='paid' + Payment record."""
        try:
            if not participant.legacy_entry_id:
                return

            # Update legacy WishlistEntry
            await self.db.execute(
                sa_update(WishlistEntry)
                .where(WishlistEntry.id == participant.legacy_entry_id)
                .values(status="paid", paid_at=paid_at)
            )

            # Check existing Payment
            existing = await self.db.execute(
                select(Payment).where(Payment.wishlist_entry_id == participant.legacy_entry_id)
            )
            payment = existing.scalar_one_or_none()

            if payment:
                payment.status = "success"
                payment.paid_at = paid_at
            else:
                legacy_request_id = campaign.legacy_request_id
                if not legacy_request_id:
                    return

                payment = Payment(
                    wishlist_entry_id=participant.legacy_entry_id,
                    user_id=participant.user_id,
                    request_id=legacy_request_id,
                    amount_try=amount_try,
                    quantity=participant.quantity,
                    status="success",
                    paid_at=paid_at,
                )
                self.db.add(payment)
        except Exception:
            logger.exception("shadow_payment_confirm failed for participant %s", participant.id)

    async def shadow_create_suggestion(self, suggestion: ProductSuggestion) -> None:
        """Legacy ProductRequest status='pending'."""
        try:
            legacy_pr = ProductRequest(
                title=suggestion.title,
                description=suggestion.description,
                category_id=suggestion.category_id,
                reference_url=suggestion.reference_url,
                expected_price_try=suggestion.expected_price_try,
                status="pending",
                created_by=suggestion.created_by,
            )
            self.db.add(legacy_pr)
        except Exception:
            logger.exception("shadow_create_suggestion failed for suggestion %s", suggestion.id)
