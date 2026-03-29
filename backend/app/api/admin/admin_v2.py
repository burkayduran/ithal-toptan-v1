"""
V2 Admin Endpoints — Campaign & Suggestion Management.
Primary source: new domain tables (campaigns, products, product_suggestions).
"""
import os
import uuid as uuid_mod
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, and_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.session import get_db
from sqlalchemy.exc import IntegrityError as SQLIntegrityError

from app.models.models import (
    Campaign, CampaignDemandEntry, CampaignParticipant, CampaignStatusHistory,
    Category, Product, ProductSuggestion, SupplierOffer, User, PaymentTransaction,
)
from app.services.campaign_helpers import is_moq_reached
from app.schemas.v2_schemas import (
    AdminCampaignDetailResponse,
    CampaignCreatePayload,
    CampaignUpdatePayload,
    CampaignResponse,
    SuggestionResponse,
    SuggestionUpdatePayload,
)
from app.schemas.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    PriceBreakdown,
    PriceCalculateRequest,
)
from app.services.price_service import PriceCalculator

router = APIRouter()


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard KPI summary for admin."""
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    # Campaign counts by status
    status_counts_result = await db.execute(
        select(Campaign.status, func.count(Campaign.id))
        .group_by(Campaign.status)
    )
    status_counts = {row[0]: row[1] for row in status_counts_result.all()}

    # Product count
    product_count_result = await db.execute(select(func.count(Product.id)))
    product_count = int(product_count_result.scalar() or 0)

    # Total demand entries (active only)
    total_demand_result = await db.execute(
        select(func.sum(CampaignDemandEntry.quantity))
        .where(CampaignDemandEntry.status == "active")
    )
    total_demand = int(total_demand_result.scalar() or 0)

    # Unique users who have left demands
    unique_users_result = await db.execute(
        select(func.count(distinct(CampaignDemandEntry.user_id)))
        .where(CampaignDemandEntry.status == "active")
    )
    unique_demand_users = int(unique_users_result.scalar() or 0)

    # Last 30 days demand entries count
    demand_30d_result = await db.execute(
        select(func.count(CampaignDemandEntry.id))
        .where(
            CampaignDemandEntry.created_at >= thirty_days_ago,
            CampaignDemandEntry.status == "active",
        )
    )
    demand_last_30d = int(demand_30d_result.scalar() or 0)

    # Pending suggestions
    pending_suggestions_result = await db.execute(
        select(func.count(ProductSuggestion.id))
        .where(ProductSuggestion.status == "pending")
    )
    pending_suggestions = int(pending_suggestions_result.scalar() or 0)

    # Revenue: sum of paid payment transactions
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(PaymentTransaction.amount_try), 0))
        .where(PaymentTransaction.status == "success")
    )
    total_revenue_try = float(revenue_result.scalar() or 0)

    # Pending collection: participants invited/joined × price (estimated)
    # Conservative approach: only count invited (moq_reached) participants with price snapshots
    pending_collection_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.total_amount_try_snapshot), 0))
        .where(
            CampaignParticipant.status == "invited",
            CampaignParticipant.total_amount_try_snapshot.isnot(None),
        )
    )
    pending_collection_try = float(pending_collection_result.scalar() or 0)

    return {
        # Campaign funnel
        "campaigns_total": sum(status_counts.values()),
        "campaigns_draft": status_counts.get("draft", 0),
        "campaigns_active": status_counts.get("active", 0),
        "campaigns_moq_reached": status_counts.get("moq_reached", 0),
        "campaigns_payment_collecting": status_counts.get("payment_collecting", 0),
        "campaigns_ordered": status_counts.get("ordered", 0),
        "campaigns_shipped": status_counts.get("shipped", 0),
        "campaigns_delivered": status_counts.get("delivered", 0),
        # Products
        "products_total": product_count,
        # Demand
        "demand_total": total_demand,
        "demand_unique_users": unique_demand_users,
        "demand_last_30d": demand_last_30d,
        # Suggestions
        "suggestions_pending": pending_suggestions,
        # Financial — may be 0 if no paid transactions yet
        "revenue_total_try": total_revenue_try,
        "pending_collection_try": pending_collection_try,
    }


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
# IMAGE UPLOAD
# ══════════════════════════════════════════════════════════════════════════

UPLOAD_DIR = "/app/uploads"
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

@router.post("/uploads/image", status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
):
    """Upload a product image. Returns the URL to use in images[]."""
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Sadece JPEG, PNG ve WebP destekleniyor. Gönderilen: {file.content_type}",
        )

    # Read and size-check
    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=422,
            detail=f"Dosya boyutu 5 MB'ı aşıyor ({len(content) // 1024} KB)",
        )

    # Extension from content_type
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map[file.content_type]
    filename = f"{uuid_mod.uuid4().hex}.{ext}"

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(UPLOAD_DIR, filename)
    with open(dest, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/{filename}", "filename": filename}


# ══════════════════════════════════════════════════════════════════════════
# DEMAND ENTRIES MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

@router.get("/campaigns/{campaign_id}/demand-entries")
async def list_demand_entries(
    campaign_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all demand entries for a campaign (admin only)."""
    result = await db.execute(
        select(CampaignDemandEntry, User)
        .join(User, CampaignDemandEntry.user_id == User.id)
        .where(CampaignDemandEntry.campaign_id == campaign_id)
        .order_by(CampaignDemandEntry.created_at.desc())
    )
    rows = result.all()

    # Summary stats
    total_quantity = sum(e.quantity for e, _ in rows if e.status == "active")
    unique_users = len(set(e.user_id for e, _ in rows if e.status == "active"))

    entries = [
        {
            "id": str(entry.id),
            "campaign_id": str(entry.campaign_id),
            "user_id": str(entry.user_id),
            "user_email": user.email,
            "user_full_name": user.full_name,
            "quantity": entry.quantity,
            "status": entry.status,
            "admin_note": entry.admin_note,
            "removal_reason": entry.removal_reason,
            "removed_at": entry.removed_at.isoformat() if entry.removed_at else None,
            "created_at": entry.created_at.isoformat(),
        }
        for entry, user in rows
    ]

    return {
        "campaign_id": str(campaign_id),
        "total_active_quantity": total_quantity,
        "unique_active_users": unique_users,
        "entries": entries,
    }


@router.patch("/demand-entries/{entry_id}")
async def update_demand_entry(
    entry_id: UUID,
    data: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Flag or add a note to a demand entry."""
    result = await db.execute(
        select(CampaignDemandEntry).where(CampaignDemandEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Demand entry not found")

    if "admin_note" in data:
        entry.admin_note = data["admin_note"]
    if "status" in data and data["status"] in ("active", "flagged"):
        entry.status = data["status"]

    await db.commit()
    return {"id": str(entry.id), "status": entry.status, "admin_note": entry.admin_note}


@router.delete("/demand-entries/{entry_id}")
async def delete_demand_entry(
    entry_id: UUID,
    reason: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a demand entry. Updates the aggregate CampaignParticipant count.
    If participant quantity drops to 0, removes participant entirely.
    """
    result = await db.execute(
        select(CampaignDemandEntry).where(CampaignDemandEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Demand entry not found")

    if entry.status == "removed":
        raise HTTPException(status_code=400, detail="Entry already removed")

    qty_to_remove = entry.quantity
    campaign_id = entry.campaign_id
    user_id = entry.user_id

    # Soft-delete the entry
    entry.status = "removed"
    entry.removed_at = datetime.now(timezone.utc)
    entry.removed_by = admin.id
    entry.removal_reason = reason

    # Update the aggregate participant
    participant_result = await db.execute(
        select(CampaignParticipant).where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.user_id == user_id,
        )
    )
    participant = participant_result.scalar_one_or_none()
    if participant:
        new_qty = max(0, participant.quantity - qty_to_remove)
        if new_qty == 0:
            await db.delete(participant)
        else:
            participant.quantity = new_qty

    await db.commit()
    return {"message": "Demand entry removed", "id": str(entry_id)}


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

    # 3. Create Campaign (without selected_offer_id yet)
    campaign = Campaign(
        product_id=product.id,
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
    await db.flush()  # campaign.id now available

    # 4. Create SupplierOffer with real campaign_id
    offer = SupplierOffer(
        campaign_id=campaign.id,
        request_id=None,
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

    # 5. Link offer to campaign
    campaign.selected_offer_id = offer.id

    # Suggestion dönüşüm bağı
    if data.from_suggestion_id:
        suggestion_result = await db.execute(
            select(ProductSuggestion).where(ProductSuggestion.id == data.from_suggestion_id)
        )
        suggestion = suggestion_result.scalar_one_or_none()
        if suggestion:
            suggestion.converted_product_id = product.id
            suggestion.status = "approved"
            suggestion.reviewed_at = datetime.now(timezone.utc)

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
    LOCKED_STATUSES = {"moq_reached", "payment_collecting", "ordered", "shipped", "delivered"}
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

    # ── Status değişikliği — explicit allowed transitions ──────────────
    if data.status is not None and data.status != campaign.status:
        old_status = campaign.status
        new_status = data.status

        ALLOWED_TRANSITIONS: dict[str, set[str]] = {
            "draft":              {"active", "cancelled"},
            "active":             {"moq_reached", "cancelled"},
            "moq_reached":        {"payment_collecting", "cancelled"},
            "payment_collecting": {"ordered", "cancelled"},
            "ordered":            {"shipped", "cancelled"},
            "shipped":            {"delivered"},
            # terminal states — no outgoing transitions
            "delivered":          set(),
            "cancelled":          set(),
        }

        allowed = ALLOWED_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"'{old_status}' → '{new_status}' geçişi yapılamaz. "
                    f"İzin verilen: {sorted(allowed) if allowed else 'yok (terminal durum)'}."
                ),
            )

        # Guard: active → moq_reached requires real DB participant count >= moq
        if old_status == "active" and new_status == "moq_reached":
            actual_count, reached = await is_moq_reached(db, campaign.id, campaign.moq or 0)
            if not reached:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"MOQ henüz dolmadı: {actual_count}/{campaign.moq} katılımcı. "
                        "Gerçek katılımcı toplamı MOQ'ya ulaşmadan bu geçiş yapılamaz."
                    ),
                )

        campaign.status = new_status

        # Timestamp'leri güncelle
        now_ts = datetime.now(timezone.utc)
        if new_status == "cancelled":
            campaign.cancelled_at = now_ts
        elif new_status == "active" and old_status == "draft":
            campaign.activated_at = now_ts
        elif new_status == "ordered":
            campaign.ordered_at = now_ts
        elif new_status == "delivered":
            campaign.delivered_at = now_ts
        # shipped_at field henüz Campaign modelinde yok; status history'de izleniyor

        # Status history kaydı
        db.add(CampaignStatusHistory(
            campaign_id=campaign.id,
            old_status=old_status,
            new_status=new_status,
            changed_by=admin.id,
            reason="admin_manual_update",
        ))

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

        if campaign.status in ("ordered", "shipped", "delivered"):
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


# ══════════════════════════════════════════════════════════════════════════
# CATEGORY MANAGEMENT (moved from v1 admin)
# ══════════════════════════════════════════════════════════════════════════

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all categories."""
    result = await db.execute(
        select(Category).order_by(Category.sort_order, Category.name)
    )
    return result.scalars().all()


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category."""
    category = Category(
        name=data.name,
        slug=data.slug,
        parent_id=data.parent_id,
        gumruk_rate=data.gumruk_rate,
        is_restricted=data.is_restricted,
        icon=data.icon,
        sort_order=data.sort_order,
    )
    db.add(category)
    try:
        await db.commit()
    except SQLIntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Bu slug zaten kullanılıyor.")
    await db.refresh(category)
    return category


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if data.name is not None:
        category.name = data.name
    if data.slug is not None:
        category.slug = data.slug
    if data.parent_id is not None:
        category.parent_id = data.parent_id
    if data.gumruk_rate is not None:
        category.gumruk_rate = data.gumruk_rate
    if data.is_restricted is not None:
        category.is_restricted = data.is_restricted
    if data.icon is not None:
        category.icon = data.icon
    if data.sort_order is not None:
        category.sort_order = data.sort_order

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category."""
    result = await db.execute(
        select(Category).where(Category.id == category_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        await db.delete(category)
        await db.commit()
    except SQLIntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Bu kategoriye atanmış ürünler var. Önce ürünleri taşıyın."
        )


# ══════════════════════════════════════════════════════════════════════════
# PRICE PREVIEW
# ══════════════════════════════════════════════════════════════════════════

@router.post("/calculate-price", response_model=PriceBreakdown)
async def calculate_price_preview(
    data: PriceCalculateRequest,
    admin: User = Depends(require_admin),
):
    """Price calculation preview."""
    calculator = PriceCalculator()
    return await calculator.calculate_selling_price(
        unit_price_usd=data.unit_price_usd,
        moq=data.moq,
        shipping_cost_usd=data.shipping_cost_usd,
        customs_rate=data.customs_rate,
        margin_rate=data.margin_rate,
    )
