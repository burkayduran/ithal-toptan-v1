"""
V2 Admin Endpoints — Campaign & Suggestion Management.
Primary source: new domain tables (campaigns, products, product_suggestions).
"""
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.session import get_db
from app.models.models import (
    Campaign, CampaignParticipant, CampaignStatusHistory,
    Product, ProductSuggestion, SupplierOffer, User,
)
from app.schemas.v2_schemas import (
    AdminCampaignDetailResponse,
    CampaignCreatePayload,
    CampaignUpdatePayload,
    CampaignResponse,
    SuggestionResponse,
    SuggestionUpdatePayload,
)
from app.services.price_service import PriceCalculator

router = APIRouter()


# ── Helper ────────────────────────────────────────────────────────────────

def _build_campaign_response(
    campaign: Campaign,
    product: Product,
    participant_count: int,
) -> CampaignResponse:
    title = campaign.title_override or product.title
    description = campaign.description_override or product.description
    images = campaign.images_override or product.images or []
    selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else None
    moq = campaign.moq or 0

    return CampaignResponse(
        id=campaign.id,
        product_id=campaign.product_id,
        title=title,
        description=description,
        category_id=product.category_id,
        images=images,
        status=campaign.status,
        view_count=campaign.view_count,
        created_at=campaign.created_at,
        activated_at=campaign.activated_at,
        moq=moq,
        selling_price_try=selling_price,
        lead_time_days=campaign.lead_time_days,
        current_participant_count=participant_count,
        moq_fill_percentage=round(participant_count / moq * 100, 1) if moq else None,
    )


# ══════════════════════════════════════════════════════════════════════════
# CAMPAIGN MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

@router.post("/campaigns", response_model=CampaignResponse, status_code=201)
async def create_campaign(
    data: CampaignCreatePayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin creates a campaign (Product + SupplierOffer + Campaign atomically).
    """
    # 1. Create Product
    product = Product(
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        images=data.images or [],
        created_by=admin.id,
    )
    db.add(product)
    await db.flush()

    # 2. Calculate price
    calculator = PriceCalculator()
    price_breakdown = await calculator.calculate_selling_price(
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        margin_rate=data.margin_rate,
    )

    # 3. Create SupplierOffer with placeholder request_id
    # Reverse DW will replace with real legacy ProductRequest ID
    placeholder_request_id = uuid_mod.uuid4()
    offer = SupplierOffer(
        request_id=placeholder_request_id,
        supplier_name=data.supplier_name,
        supplier_country=data.supplier_country,
        alibaba_product_url=data.alibaba_product_url,
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        lead_time_days=data.lead_time_days,
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        usd_rate_used=float(price_breakdown.usd_rate),
        selling_price_try=float(price_breakdown.selling_price_try),
        margin_rate=data.margin_rate,
        is_selected=True,
    )
    db.add(offer)
    await db.flush()

    # 4. Create Campaign with snapshots
    campaign = Campaign(
        product_id=product.id,
        selected_offer_id=offer.id,
        status="draft",
        supplier_name_snapshot=data.supplier_name,
        supplier_country_snapshot=data.supplier_country,
        alibaba_product_url_snapshot=data.alibaba_product_url,
        unit_price_usd_snapshot=data.unit_price_usd,
        shipping_cost_usd_snapshot=data.shipping_cost_usd,
        customs_rate_snapshot=data.customs_rate,
        margin_rate_snapshot=data.margin_rate,
        fx_rate_snapshot=float(price_breakdown.usd_rate),
        selling_price_try_snapshot=float(price_breakdown.selling_price_try),
        moq=data.moq,
        lead_time_days=data.lead_time_days,
        created_by=admin.id,
    )
    db.add(campaign)
    await db.flush()

    # Reverse dual-write: create legacy ProductRequest
    try:
        from app.services.reverse_dual_write import ReverseDualWrite
        rdw = ReverseDualWrite(db)
        await rdw.shadow_create_campaign(campaign, product, offer, admin.id)
    except Exception:
        pass

    await db.commit()
    await db.refresh(campaign)
    await db.refresh(product)

    return _build_campaign_response(campaign, product, 0)


@router.post("/campaigns/{campaign_id}/publish")
async def publish_campaign(
    campaign_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Publish campaign: draft → active."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is already {campaign.status}",
        )

    # Validate snapshot fields are filled
    if not campaign.selling_price_try_snapshot or not campaign.moq:
        raise HTTPException(
            status_code=400,
            detail="Campaign must have price and MOQ before publishing",
        )

    old_status = campaign.status
    campaign.status = "active"
    campaign.activated_at = datetime.now(timezone.utc)

    # Status history
    db.add(CampaignStatusHistory(
        campaign_id=campaign.id,
        old_status=old_status,
        new_status="active",
        reason="admin_publish",
        changed_by=admin.id,
    ))

    # Reverse dual-write: legacy publish
    try:
        from app.services.reverse_dual_write import ReverseDualWrite
        rdw = ReverseDualWrite(db)
        await rdw.shadow_publish_campaign(campaign)
    except Exception:
        pass

    await db.commit()

    return {"message": "Campaign published successfully", "id": str(campaign_id)}


@router.get("/campaigns", response_model=List[CampaignResponse])
async def list_all_campaigns(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin lists all campaigns (including drafts)."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .order_by(Campaign.created_at.desc())
    )
    rows = result.all()

    if not rows:
        return []

    # Batch participant counts
    campaign_ids = [c.id for c, _ in rows]
    count_result = await db.execute(
        select(
            CampaignParticipant.campaign_id,
            func.coalesce(func.sum(CampaignParticipant.quantity), 0),
        )
        .where(
            CampaignParticipant.campaign_id.in_(campaign_ids),
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
        .group_by(CampaignParticipant.campaign_id)
    )
    counts_map = {row[0]: int(row[1]) for row in count_result.all()}

    return [
        _build_campaign_response(c, p, counts_map.get(c.id, 0))
        for c, p in rows
    ]


async def _get_detail_response(campaign_id: UUID, db: AsyncSession) -> AdminCampaignDetailResponse:
    """Shared helper for returning full campaign detail."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row

    count_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
        .where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
    )
    participant_count = int(count_result.scalar() or 0)

    title = campaign.title_override or product.title
    description = campaign.description_override or product.description
    images = campaign.images_override or product.images or []
    selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else None
    moq = campaign.moq or 0

    return AdminCampaignDetailResponse(
        id=campaign.id,
        product_id=campaign.product_id,
        title=title,
        description=description,
        category_id=product.category_id,
        images=images,
        status=campaign.status,
        view_count=campaign.view_count,
        created_at=campaign.created_at,
        activated_at=campaign.activated_at,
        moq=moq,
        selling_price_try=selling_price,
        lead_time_days=campaign.lead_time_days,
        current_participant_count=participant_count,
        moq_fill_percentage=round(participant_count / moq * 100, 1) if moq else None,
        selected_offer_id=campaign.selected_offer_id,
        supplier_name_snapshot=campaign.supplier_name_snapshot,
        supplier_country_snapshot=campaign.supplier_country_snapshot,
        alibaba_product_url_snapshot=campaign.alibaba_product_url_snapshot,
        unit_price_usd_snapshot=float(campaign.unit_price_usd_snapshot) if campaign.unit_price_usd_snapshot else None,
        shipping_cost_usd_snapshot=float(campaign.shipping_cost_usd_snapshot) if campaign.shipping_cost_usd_snapshot else None,
        customs_rate_snapshot=float(campaign.customs_rate_snapshot) if campaign.customs_rate_snapshot else None,
        margin_rate_snapshot=float(campaign.margin_rate_snapshot) if campaign.margin_rate_snapshot else None,
        fx_rate_snapshot=float(campaign.fx_rate_snapshot) if campaign.fx_rate_snapshot else None,
        moq_reached_at=campaign.moq_reached_at,
        payment_deadline=campaign.payment_deadline,
        ordered_at=campaign.ordered_at,
        delivered_at=campaign.delivered_at,
    )


@router.get("/campaigns/{campaign_id}", response_model=AdminCampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin gets full campaign detail with snapshot fields."""
    return await _get_detail_response(campaign_id, db)


@router.patch("/campaigns/{campaign_id}", response_model=AdminCampaignDetailResponse)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdatePayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin updates a campaign — pricing/supplier changes only in draft/active."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row

    # Lock pricing fields if payment phase started
    LOCKED_STATUSES = {"moq_reached", "payment_collecting", "ordered"}
    PRICING_FIELDS = [
        "unit_price_usd", "moq", "shipping_cost_usd", "customs_rate",
        "margin_rate", "supplier_name", "supplier_country", "alibaba_product_url",
    ]
    if campaign.status in LOCKED_STATUSES:
        for field_name in PRICING_FIELDS:
            if getattr(data, field_name, None) is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Ödeme süreci başlamış kampanyalarda fiyat ve tedarikçi bilgileri değiştirilemez.",
                )

    # Track if pricing changed for recalculation
    pricing_changed = False

    # Update product fields (title, description, category, images)
    if data.title is not None:
        product.title = data.title
    if data.description is not None:
        product.description = data.description
    if data.category_id is not None:
        product.category_id = data.category_id
    if data.images is not None:
        product.images = data.images

    # Update supplier/pricing snapshot fields
    if data.supplier_name is not None:
        campaign.supplier_name_snapshot = data.supplier_name
    if data.supplier_country is not None:
        campaign.supplier_country_snapshot = data.supplier_country
    if data.alibaba_product_url is not None:
        campaign.alibaba_product_url_snapshot = data.alibaba_product_url

    if data.unit_price_usd is not None:
        campaign.unit_price_usd_snapshot = data.unit_price_usd
        pricing_changed = True
    if data.moq is not None:
        campaign.moq = data.moq
        pricing_changed = True
    if data.shipping_cost_usd is not None:
        campaign.shipping_cost_usd_snapshot = data.shipping_cost_usd
        pricing_changed = True
    if data.customs_rate is not None:
        campaign.customs_rate_snapshot = data.customs_rate
        pricing_changed = True
    if data.margin_rate is not None:
        campaign.margin_rate_snapshot = data.margin_rate
        pricing_changed = True
    if data.lead_time_days is not None:
        campaign.lead_time_days = data.lead_time_days

    # Recalculate selling price if pricing inputs changed
    if pricing_changed:
        calculator = PriceCalculator()
        price = await calculator.calculate_selling_price(
            unit_price_usd=float(campaign.unit_price_usd_snapshot or 0),
            moq=int(campaign.moq or 1),
            shipping_cost_usd=float(campaign.shipping_cost_usd_snapshot or 0),
            customs_rate=float(campaign.customs_rate_snapshot or 0.35),
            margin_rate=float(campaign.margin_rate_snapshot or 0.30),
        )
        campaign.fx_rate_snapshot = float(price.usd_rate)
        campaign.selling_price_try_snapshot = float(price.selling_price_try)

        # Also update the linked SupplierOffer
        if campaign.selected_offer_id:
            offer_result = await db.execute(
                select(SupplierOffer).where(SupplierOffer.id == campaign.selected_offer_id)
            )
            offer = offer_result.scalar_one_or_none()
            if offer:
                if data.unit_price_usd is not None:
                    offer.unit_price_usd = data.unit_price_usd
                if data.moq is not None:
                    offer.moq = data.moq
                if data.shipping_cost_usd is not None:
                    offer.shipping_cost_usd = data.shipping_cost_usd
                if data.customs_rate is not None:
                    offer.customs_rate = data.customs_rate
                if data.margin_rate is not None:
                    offer.margin_rate = data.margin_rate
                if data.supplier_name is not None:
                    offer.supplier_name = data.supplier_name
                if data.supplier_country is not None:
                    offer.supplier_country = data.supplier_country
                offer.usd_rate_used = float(price.usd_rate)
                offer.selling_price_try = float(price.selling_price_try)

    # Reverse dual-write
    try:
        from app.services.reverse_dual_write import ReverseDualWrite
        rdw = ReverseDualWrite(db)
        await rdw.shadow_update_campaign(campaign, product)
    except Exception:
        pass

    await db.commit()
    await db.refresh(campaign)
    await db.refresh(product)

    return await _get_detail_response(campaign_id, db)


# ── Bulk Operations ──────────────────────────────────────────────────────

@router.post("/campaigns/bulk-publish")
async def bulk_publish_campaigns(
    campaign_ids: List[UUID],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk publish draft campaigns."""
    published = []
    failed = []

    for cid in campaign_ids:
        result = await db.execute(
            select(Campaign).where(Campaign.id == cid)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            failed.append({"id": str(cid), "reason": "Kampanya bulunamadı"})
            continue

        if campaign.status != "draft":
            failed.append({"id": str(cid), "reason": f"Durum zaten '{campaign.status}'"})
            continue

        if not campaign.selling_price_try_snapshot or not campaign.moq:
            failed.append({"id": str(cid), "reason": "Fiyat veya MOQ eksik"})
            continue

        old_status = campaign.status
        campaign.status = "active"
        campaign.activated_at = datetime.now(timezone.utc)

        db.add(CampaignStatusHistory(
            campaign_id=campaign.id,
            old_status=old_status,
            new_status="active",
            reason="bulk_publish",
            changed_by=admin.id,
        ))

        try:
            from app.services.reverse_dual_write import ReverseDualWrite
            rdw = ReverseDualWrite(db)
            await rdw.shadow_publish_campaign(campaign)
        except Exception:
            pass

        published.append(str(cid))

    await db.commit()
    return {"published": published, "failed": failed}


@router.post("/campaigns/bulk-cancel")
async def bulk_cancel_campaigns(
    campaign_ids: List[UUID],
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bulk cancel campaigns."""
    cancelled = []
    failed = []

    for cid in campaign_ids:
        result = await db.execute(
            select(Campaign).where(Campaign.id == cid)
        )
        campaign = result.scalar_one_or_none()

        if not campaign:
            failed.append({"id": str(cid), "reason": "Kampanya bulunamadı"})
            continue

        if campaign.status in ("ordered", "delivered"):
            failed.append({"id": str(cid), "reason": f"'{campaign.status}' durumundaki kampanya iptal edilemez"})
            continue

        old_status = campaign.status
        campaign.status = "cancelled"
        campaign.cancelled_at = datetime.now(timezone.utc)

        db.add(CampaignStatusHistory(
            campaign_id=campaign.id,
            old_status=old_status,
            new_status="cancelled",
            reason="bulk_cancel",
            changed_by=admin.id,
        ))

        try:
            from app.services.reverse_dual_write import ReverseDualWrite
            rdw = ReverseDualWrite(db)
            await rdw.shadow_campaign_status(campaign, "cancelled")
        except Exception:
            pass

        cancelled.append(str(cid))

    await db.commit()
    return {"cancelled": cancelled, "failed": failed}


# ══════════════════════════════════════════════════════════════════════════
# SUGGESTION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

@router.get("/suggestions", response_model=List[SuggestionResponse])
async def list_suggestions(
    status: str = "pending",
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin lists product suggestions by status."""
    result = await db.execute(
        select(ProductSuggestion)
        .where(ProductSuggestion.status == status)
        .order_by(ProductSuggestion.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/suggestions/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    suggestion_id: UUID,
    data: SuggestionUpdatePayload,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin updates a suggestion (approve/reject)."""
    result = await db.execute(
        select(ProductSuggestion).where(ProductSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if data.status is not None:
        suggestion.status = data.status
        if data.status in ("approved", "rejected"):
            suggestion.reviewed_at = datetime.now(timezone.utc)
    if data.admin_notes is not None:
        suggestion.admin_notes = data.admin_notes

    await db.commit()
    await db.refresh(suggestion)
    return suggestion
