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


@router.get("/campaigns/{campaign_id}", response_model=AdminCampaignDetailResponse)
async def get_campaign_detail(
    campaign_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin gets full campaign detail with snapshot fields."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row

    # Participant count
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
        # Snapshot fields
        selected_offer_id=campaign.selected_offer_id,
        supplier_name_snapshot=campaign.supplier_name_snapshot,
        supplier_country_snapshot=campaign.supplier_country_snapshot,
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
