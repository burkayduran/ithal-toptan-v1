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
from sqlalchemy import func, select, and_, distinct, case, Integer
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
    """Operational cockpit dashboard — KPIs, attention items, lifecycle, finance, demand."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    three_days_from_now = now + timedelta(days=3)

    # ── Campaign counts by status ─────────────────────────────────────────────
    status_counts_result = await db.execute(
        select(Campaign.status, func.count(Campaign.id)).group_by(Campaign.status)
    )
    status_counts = {row[0]: row[1] for row in status_counts_result.all()}

    campaigns_active = status_counts.get("active", 0)
    campaigns_draft = status_counts.get("draft", 0)
    campaigns_moq_reached = status_counts.get("moq_reached", 0)
    campaigns_payment_collecting = status_counts.get("payment_collecting", 0)
    campaigns_ordered = status_counts.get("ordered", 0)
    campaigns_shipped = status_counts.get("shipped", 0)
    campaigns_delivered = status_counts.get("delivered", 0)
    campaigns_cancelled = status_counts.get("cancelled", 0)

    # ── Product counts ────────────────────────────────────────────────────────
    product_count_result = await db.execute(select(func.count(Product.id)))
    product_count = int(product_count_result.scalar() or 0)

    products_7d_result = await db.execute(
        select(func.count(Product.id)).where(Product.created_at >= seven_days_ago)
    )
    products_delta_7d = int(products_7d_result.scalar() or 0)

    products_30d_result = await db.execute(
        select(func.count(Product.id)).where(Product.created_at >= thirty_days_ago)
    )
    products_delta_30d = int(products_30d_result.scalar() or 0)

    # Campaigns created in last 7d (active only)
    active_7d_result = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.status == "active",
            Campaign.activated_at >= seven_days_ago,
        )
    )
    active_delta_7d = int(active_7d_result.scalar() or 0)

    # ── Demand metrics ────────────────────────────────────────────────────────
    total_demand_result = await db.execute(
        select(func.sum(CampaignDemandEntry.quantity))
        .where(CampaignDemandEntry.status == "active")
    )
    total_demand = int(total_demand_result.scalar() or 0)

    unique_users_result = await db.execute(
        select(func.count(distinct(CampaignDemandEntry.user_id)))
        .where(CampaignDemandEntry.status == "active")
    )
    unique_demand_users = int(unique_users_result.scalar() or 0)

    demand_30d_result = await db.execute(
        select(func.sum(CampaignDemandEntry.quantity))
        .where(
            CampaignDemandEntry.created_at >= thirty_days_ago,
            CampaignDemandEntry.status == "active",
        )
    )
    demand_last_30d = int(demand_30d_result.scalar() or 0)

    demand_7d_result = await db.execute(
        select(func.sum(CampaignDemandEntry.quantity))
        .where(
            CampaignDemandEntry.created_at >= seven_days_ago,
            CampaignDemandEntry.status == "active",
        )
    )
    demand_last_7d = int(demand_7d_result.scalar() or 0)

    avg_demand_per_user = round(total_demand / unique_demand_users, 2) if unique_demand_users > 0 else 0.0

    # ── Suggestions ───────────────────────────────────────────────────────────
    pending_suggestions_result = await db.execute(
        select(func.count(ProductSuggestion.id)).where(ProductSuggestion.status == "pending")
    )
    pending_suggestions = int(pending_suggestions_result.scalar() or 0)

    # ── Finance ───────────────────────────────────────────────────────────────
    revenue_result = await db.execute(
        select(func.coalesce(func.sum(PaymentTransaction.amount_try), 0))
        .where(PaymentTransaction.status == "success")
    )
    total_revenue_try = float(revenue_result.scalar() or 0)

    pending_collection_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.total_amount_try_snapshot), 0))
        .where(
            CampaignParticipant.status == "invited",
            CampaignParticipant.total_amount_try_snapshot.isnot(None),
        )
    )
    pending_collection_try = float(pending_collection_result.scalar() or 0)

    # Participant counts
    invited_count_result = await db.execute(
        select(func.count(CampaignParticipant.id))
        .where(CampaignParticipant.status == "invited")
    )
    invited_participant_count = int(invited_count_result.scalar() or 0)

    paid_count_result = await db.execute(
        select(func.count(CampaignParticipant.id))
        .where(CampaignParticipant.status == "paid")
    )
    paid_participant_count = int(paid_count_result.scalar() or 0)

    # Average paid order value
    avg_order_result = await db.execute(
        select(func.avg(PaymentTransaction.amount_try))
        .where(PaymentTransaction.status == "success")
    )
    avg_paid_order_value = float(avg_order_result.scalar() or 0)

    # Payment conversion rate: paid / (invited + paid)
    conversion_denom = invited_participant_count + paid_participant_count
    payment_conversion_rate = (
        round(paid_participant_count / conversion_denom * 100, 1)
        if conversion_denom > 0 else None
    )

    # ── MOQ fill % for active campaigns (for attention + lifecycle) ───────────
    participant_qty_result = await db.execute(
        select(
            CampaignParticipant.campaign_id,
            func.sum(CampaignParticipant.quantity).label("total_qty"),
        )
        .where(CampaignParticipant.status.in_(["joined", "invited", "paid"]))
        .group_by(CampaignParticipant.campaign_id)
    )
    part_qty_map = {str(r.campaign_id): int(r.total_qty or 0) for r in participant_qty_result.all()}

    active_camps_result = await db.execute(
        select(Campaign.id, Campaign.moq, Campaign.title_override, Campaign.product_id, Campaign.payment_deadline)
        .where(Campaign.status == "active")
    )
    active_camps = active_camps_result.all()

    # Collect product titles needed
    product_ids_needed = [str(c.product_id) for c in active_camps]
    if product_ids_needed:
        prod_title_result = await db.execute(
            select(Product.id, Product.title).where(Product.id.in_([c.product_id for c in active_camps]))
        )
        prod_title_map = {str(p.id): p.title for p in prod_title_result.all()}
    else:
        prod_title_map = {}

    near_moq_items = []  # fill_pct >= 80 active
    for c in active_camps:
        qty = part_qty_map.get(str(c.id), 0)
        if c.moq and c.moq > 0:
            pct = qty / c.moq * 100
            if pct >= 80:
                title = c.title_override or prod_title_map.get(str(c.product_id), str(c.id)[:8])
                near_moq_items.append({
                    "campaign_id": str(c.id),
                    "title": title,
                    "fill_pct": round(pct, 1),
                    "current_qty": qty,
                    "moq": c.moq,
                })
    near_moq_items.sort(key=lambda x: x["fill_pct"], reverse=True)

    # MOQ stalled: moq_reached status, moq_reached_at > 24h ago
    stalled_result = await db.execute(
        select(Campaign.id, Campaign.title_override, Campaign.product_id, Campaign.moq_reached_at)
        .where(
            Campaign.status == "moq_reached",
            Campaign.moq_reached_at <= now - timedelta(hours=24),
        )
        .order_by(Campaign.moq_reached_at.asc())
        .limit(5)
    )
    stalled_rows = stalled_result.all()

    # Payment collecting with deadline <= 3 days
    urgent_payment_result = await db.execute(
        select(Campaign.id, Campaign.title_override, Campaign.product_id, Campaign.payment_deadline)
        .where(
            Campaign.status == "payment_collecting",
            Campaign.payment_deadline.isnot(None),
            Campaign.payment_deadline <= three_days_from_now,
        )
        .order_by(Campaign.payment_deadline.asc())
        .limit(5)
    )
    urgent_payment_rows = urgent_payment_result.all()

    # Fetch product titles for stalled + urgent
    extra_product_ids = (
        [r.product_id for r in stalled_rows] +
        [r.product_id for r in urgent_payment_rows]
    )
    if extra_product_ids:
        extra_prod_result = await db.execute(
            select(Product.id, Product.title).where(Product.id.in_(extra_product_ids))
        )
        for p in extra_prod_result.all():
            prod_title_map[str(p.id)] = p.title

    # Fraud watch: count critical+high risk entries
    fraud_agg_result = await db.execute(
        select(
            CampaignDemandEntry.user_id,
            CampaignDemandEntry.campaign_id,
            func.sum(CampaignDemandEntry.quantity).label("user_total_qty"),
        )
        .group_by(CampaignDemandEntry.user_id, CampaignDemandEntry.campaign_id)
    )
    fraud_raw = fraud_agg_result.all()

    fraud_campaign_ids = list({r.campaign_id for r in fraud_raw})
    fraud_moq_map: dict = {}
    if fraud_campaign_ids:
        fraud_camp_result = await db.execute(
            select(Campaign.id, Campaign.moq).where(Campaign.id.in_(fraud_campaign_ids))
        )
        fraud_moq_map = {str(c.id): c.moq for c in fraud_camp_result.all()}

    fraud_critical = 0
    fraud_high = 0
    fraud_watch_total = 0
    for r in fraud_raw:
        moq = fraud_moq_map.get(str(r.campaign_id))
        if not moq or moq <= 0:
            continue
        pct = int(r.user_total_qty or 0) / moq
        if pct >= 0.30:
            fraud_critical += 1
            fraud_watch_total += 1
        elif pct >= 0.20:
            fraud_high += 1
            fraud_watch_total += 1
        elif pct >= 0.10:
            fraud_watch_total += 1

    # ── Build attention items ─────────────────────────────────────────────────
    attention = []

    if fraud_critical > 0:
        attention.append({
            "severity": "critical",
            "title": f"{fraud_critical} kritik fraud riski",
            "description": f"MOQ'nun %30+'unu tek başına alan {fraud_critical} kullanıcı tespit edildi",
            "href": "/admin/fraud-watch",
            "primaryActionLabel": "Fraud Watch",
            "primaryActionHref": "/admin/fraud-watch",
        })
    elif fraud_high > 0:
        attention.append({
            "severity": "warning",
            "title": f"{fraud_high} yüksek fraud riski",
            "description": f"MOQ'nun %20+'unu alan {fraud_high} kullanıcı var",
            "href": "/admin/fraud-watch",
            "primaryActionLabel": "İncele",
            "primaryActionHref": "/admin/fraud-watch",
        })

    if stalled_rows:
        attention.append({
            "severity": "warning",
            "title": f"{len(stalled_rows)} kampanya ödeme aşamasına geçmedi",
            "description": "MOQ dolmuş fakat ödeme süreci başlatılmamış",
            "href": "/admin/products?status=moq_reached",
            "primaryActionLabel": "Geç",
            "primaryActionHref": "/admin/products?status=moq_reached",
        })

    if urgent_payment_rows:
        attention.append({
            "severity": "critical",
            "title": f"{len(urgent_payment_rows)} kampanyanın ödeme deadline'ı yakın",
            "description": "3 gün içinde ödeme kapanacak kampanyalar",
            "href": "/admin/products?status=payment_collecting",
            "primaryActionLabel": "İncele",
            "primaryActionHref": "/admin/products?status=payment_collecting",
        })

    if near_moq_items:
        attention.append({
            "severity": "info",
            "title": f"{len(near_moq_items)} kampanya MOQ'a %80+ yaklaştı",
            "description": "Yakında ödeme sürecine geçebilir",
            "href": "/admin/products?status=active",
            "primaryActionLabel": "Gör",
            "primaryActionHref": "/admin/products?status=active",
        })

    if pending_suggestions > 0:
        attention.append({
            "severity": "info",
            "title": f"{pending_suggestions} bekleyen ürün isteği",
            "description": "Kullanıcı önerileri inceleme bekliyor",
            "href": "/admin/product-requests?status=pending",
            "primaryActionLabel": "İncele",
            "primaryActionHref": "/admin/product-requests?status=pending",
        })

    # ── Lifecycle array ───────────────────────────────────────────────────────
    lifecycle = [
        {"status": "draft", "label": "Taslak", "count": campaigns_draft, "href": "/admin/products?status=draft"},
        {"status": "active", "label": "Aktif", "count": campaigns_active, "href": "/admin/products?status=active"},
        {"status": "moq_reached", "label": "MOQ Doldu", "count": campaigns_moq_reached, "href": "/admin/products?status=moq_reached"},
        {"status": "payment_collecting", "label": "Ödeme Topl.", "count": campaigns_payment_collecting, "href": "/admin/products?status=payment_collecting"},
        {"status": "ordered", "label": "Sipariş", "count": campaigns_ordered, "href": "/admin/products?status=ordered"},
        {"status": "shipped", "label": "Kargoda", "count": campaigns_shipped, "href": "/admin/products?status=shipped"},
        {"status": "delivered", "label": "Teslim", "count": campaigns_delivered, "href": "/admin/products?status=delivered"},
    ]

    return {
        # ── Legacy flat fields (backward compat) ──────────────────────────────
        "campaigns_total": sum(status_counts.values()),
        "campaigns_draft": campaigns_draft,
        "campaigns_active": campaigns_active,
        "campaigns_moq_reached": campaigns_moq_reached,
        "campaigns_payment_collecting": campaigns_payment_collecting,
        "campaigns_ordered": campaigns_ordered,
        "campaigns_shipped": campaigns_shipped,
        "campaigns_delivered": campaigns_delivered,
        "products_total": product_count,
        "demand_total": total_demand,
        "demand_unique_users": unique_demand_users,
        "demand_last_30d": demand_last_30d,
        "suggestions_pending": pending_suggestions,
        "revenue_total_try": total_revenue_try,
        "pending_collection_try": pending_collection_try,
        # ── New structured fields ─────────────────────────────────────────────
        "kpis": {
            "total_products": {
                "value": product_count,
                "delta_7d": products_delta_7d,
                "delta_30d": products_delta_30d,
                "hint": f"Son 7 günde +{products_delta_7d}" if products_delta_7d else "Bu hafta değişiklik yok",
                "href": "/admin/products",
            },
            "active_campaigns": {
                "value": campaigns_active,
                "delta_7d": active_delta_7d,
                "hint": f"{near_moq_items[0]['title'][:20]}… %{near_moq_items[0]['fill_pct']} doldu" if near_moq_items else "Aktif kampanya",
                "href": "/admin/products?status=active",
            },
            "moq_reached": {
                "value": campaigns_moq_reached,
                "delta_7d": None,
                "hint": f"{len(stalled_rows)} bekliyor" if stalled_rows else "Ödeme bekliyor",
                "href": "/admin/products?status=moq_reached",
            },
            "payment_collecting": {
                "value": campaigns_payment_collecting,
                "delta_7d": None,
                "hint": f"{len(urgent_payment_rows)} deadline yakın" if urgent_payment_rows else "Ödeme toplanıyor",
                "href": "/admin/products?status=payment_collecting",
            },
            "pending_suggestions": {
                "value": pending_suggestions,
                "delta_7d": None,
                "hint": "İnceleme bekliyor" if pending_suggestions else "Temiz",
                "href": "/admin/product-requests?status=pending",
            },
            "fraud_watch": {
                "value": fraud_watch_total,
                "critical": fraud_critical,
                "high": fraud_high,
                "hint": f"{fraud_critical} kritik" if fraud_critical > 0 else ("Temiz" if fraud_watch_total == 0 else f"{fraud_watch_total} şüpheli"),
                "href": "/admin/fraud-watch",
            },
        },
        "attention": attention,
        "lifecycle": lifecycle,
        "finance": {
            "collected_amount": total_revenue_try,
            "pending_amount": pending_collection_try,
            "payment_conversion_rate": payment_conversion_rate,
            "average_paid_order_value": round(avg_paid_order_value, 2) if avg_paid_order_value else None,
            "invited_participant_count": invited_participant_count,
            "paid_participant_count": paid_participant_count,
        },
        "demand": {
            "total_quantity": total_demand,
            "unique_users": unique_demand_users,
            "average_per_user": avg_demand_per_user,
            "last_30_days_quantity": demand_last_30d,
            "last_7_days_quantity": demand_last_7d,
        },
        "near_moq_active": near_moq_items[:6],
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
# DEMAND USERS — kullanıcı bazlı aggregate talep analizi
# ══════════════════════════════════════════════════════════════════════════

@router.get("/demand-users")
async def list_demand_users(
    sort: str = Query("quantity_desc", description="quantity_desc | recent | campaigns | flagged"),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcı bazında aggregate demand istatistikleri."""
    # Aggregate per user
    agg_result = await db.execute(
        select(
            CampaignDemandEntry.user_id,
            func.count(CampaignDemandEntry.id).label("total_entries"),
            func.coalesce(func.sum(CampaignDemandEntry.quantity), 0).label("total_quantity"),
            func.count(distinct(CampaignDemandEntry.campaign_id)).label("unique_campaigns"),
            func.max(CampaignDemandEntry.quantity).label("max_single_entry_qty"),
            func.max(CampaignDemandEntry.created_at).label("last_activity"),
            func.sum(
                case((CampaignDemandEntry.status == "flagged", 1), else_=0)
            ).label("flagged_count"),
            func.sum(
                case((CampaignDemandEntry.status == "removed", 1), else_=0)
            ).label("removed_count"),
        )
        .group_by(CampaignDemandEntry.user_id)
    )
    rows = agg_result.all()

    if not rows:
        return {"users": [], "total": 0}

    user_ids = [r.user_id for r in rows]
    user_result = await db.execute(
        select(User.id, User.email, User.full_name)
        .where(User.id.in_(user_ids))
    )
    user_map = {u.id: {"email": u.email, "full_name": u.full_name} for u in user_result.all()}

    users = []
    for r in rows:
        info = user_map.get(r.user_id, {})
        users.append({
            "user_id": str(r.user_id),
            "email": info.get("email", ""),
            "full_name": info.get("full_name"),
            "total_entries": int(r.total_entries),
            "total_quantity": int(r.total_quantity),
            "unique_campaigns": int(r.unique_campaigns),
            "max_single_entry_qty": int(r.max_single_entry_qty or 0),
            "last_activity": r.last_activity.isoformat() if r.last_activity else None,
            "flagged_count": int(r.flagged_count or 0),
            "removed_count": int(r.removed_count or 0),
        })

    # Sort
    if sort == "quantity_desc":
        users.sort(key=lambda x: x["total_quantity"], reverse=True)
    elif sort == "recent":
        users.sort(key=lambda x: x["last_activity"] or "", reverse=True)
    elif sort == "campaigns":
        users.sort(key=lambda x: x["unique_campaigns"], reverse=True)
    elif sort == "flagged":
        users.sort(key=lambda x: x["flagged_count"], reverse=True)

    return {"users": users, "total": len(users)}


@router.get("/demand-users/{user_id}")
async def get_demand_user_detail(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Kullanıcının tüm kampanyalardaki demand geçmişini döndür."""
    user_result = await db.execute(select(User).where(User.id == user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    entries_result = await db.execute(
        select(CampaignDemandEntry, Campaign)
        .join(Campaign, CampaignDemandEntry.campaign_id == Campaign.id)
        .where(CampaignDemandEntry.user_id == user_id)
        .order_by(CampaignDemandEntry.created_at.desc())
    )
    rows = entries_result.all()

    # Fetch product titles for campaigns
    product_ids = list({c.product_id for _, c in rows})
    prod_result = await db.execute(
        select(Product.id, Product.title).where(Product.id.in_(product_ids))
    )
    prod_map = {p.id: p.title for p in prod_result.all()}

    # Group by campaign
    from collections import defaultdict
    camp_groups: dict = defaultdict(list)
    camp_meta: dict = {}
    for entry, campaign in rows:
        cid = str(campaign.id)
        camp_groups[cid].append(entry)
        camp_meta[cid] = campaign

    campaigns_out = []
    for cid, entries in camp_groups.items():
        camp = camp_meta[cid]
        title = camp.title_override or prod_map.get(camp.product_id, cid[:8])
        active_qty = sum(e.quantity for e in entries if e.status == "active")
        flagged = sum(1 for e in entries if e.status == "flagged")
        removed = sum(1 for e in entries if e.status == "removed")
        last_act = max(e.created_at for e in entries)

        campaigns_out.append({
            "campaign_id": cid,
            "campaign_title": title,
            "campaign_status": camp.status,
            "campaign_moq": camp.moq,
            "total_active_quantity": active_qty,
            "entry_count": len(entries),
            "flagged_count": flagged,
            "removed_count": removed,
            "last_activity": last_act.isoformat(),
            "entries": [
                {
                    "id": str(e.id),
                    "quantity": e.quantity,
                    "status": e.status,
                    "admin_note": e.admin_note,
                    "removal_reason": e.removal_reason,
                    "removed_at": e.removed_at.isoformat() if e.removed_at else None,
                    "created_at": e.created_at.isoformat(),
                }
                for e in sorted(entries, key=lambda x: x.created_at, reverse=True)
            ],
        })

    # Sort campaigns by last activity desc
    campaigns_out.sort(key=lambda x: x["last_activity"], reverse=True)

    return {
        "user_id": str(target_user.id),
        "email": target_user.email,
        "full_name": target_user.full_name,
        "created_at": target_user.created_at.isoformat() if target_user.created_at else None,
        "campaigns": campaigns_out,
        "totals": {
            "total_entries": len(rows),
            "total_active_quantity": sum(e.quantity for e, _ in rows if e.status == "active"),
            "unique_campaigns": len(camp_groups),
            "flagged_count": sum(1 for e, _ in rows if e.status == "flagged"),
            "removed_count": sum(1 for e, _ in rows if e.status == "removed"),
        },
    }


# ══════════════════════════════════════════════════════════════════════════
# FRAUD WATCH — MOQ %10+ risk tespiti
# ══════════════════════════════════════════════════════════════════════════

FRAUD_WATCH_THRESHOLD = 0.10   # %10
FRAUD_HIGH_THRESHOLD = 0.20    # %20
FRAUD_CRITICAL_THRESHOLD = 0.30  # %30

@router.get("/fraud-watch")
async def get_fraud_watch(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    MOQ'nun %10+'unu tek başına alan kullanıcıları ve diğer fraud sinyallerini döndür.
    Eşik: user_total_quantity >= campaign.moq * 0.10
    """
    # Per user-campaign aggregate
    agg_result = await db.execute(
        select(
            CampaignDemandEntry.user_id,
            CampaignDemandEntry.campaign_id,
            func.sum(CampaignDemandEntry.quantity).label("user_total_qty"),
            func.count(CampaignDemandEntry.id).label("entry_count"),
            func.sum(
                case((CampaignDemandEntry.status == "flagged", 1), else_=0)
            ).label("flagged_count"),
            func.sum(
                case((CampaignDemandEntry.status == "removed", 1), else_=0)
            ).label("removed_count"),
            func.max(CampaignDemandEntry.created_at).label("last_activity"),
        )
        .group_by(CampaignDemandEntry.user_id, CampaignDemandEntry.campaign_id)
    )
    raw_rows = agg_result.all()

    if not raw_rows:
        return {"entries": [], "total": 0, "threshold_pct": int(FRAUD_WATCH_THRESHOLD * 100)}

    # Fetch campaigns
    campaign_ids = list({r.campaign_id for r in raw_rows})
    campaigns_result = await db.execute(
        select(Campaign.id, Campaign.moq, Campaign.title_override, Campaign.status, Campaign.product_id)
        .where(Campaign.id.in_(campaign_ids))
    )
    campaign_map = {}
    product_ids = []
    for c in campaigns_result.all():
        campaign_map[c.id] = {
            "moq": c.moq, "title_override": c.title_override,
            "status": c.status, "product_id": c.product_id,
        }
        product_ids.append(c.product_id)

    # Fetch product titles for campaigns without title_override
    products_result = await db.execute(
        select(Product.id, Product.title).where(Product.id.in_(product_ids))
    )
    product_map = {p.id: p.title for p in products_result.all()}

    # Fetch users
    user_ids = list({r.user_id for r in raw_rows})
    users_result = await db.execute(
        select(User.id, User.email, User.full_name).where(User.id.in_(user_ids))
    )
    user_map = {u.id: {"email": u.email, "full_name": u.full_name} for u in users_result.all()}

    entries = []
    for r in raw_rows:
        camp = campaign_map.get(r.campaign_id)
        if not camp:
            continue
        moq = camp["moq"]
        if not moq or moq <= 0:
            continue

        user_total_qty = int(r.user_total_qty or 0)
        percent_of_moq = user_total_qty / moq

        if percent_of_moq < FRAUD_WATCH_THRESHOLD:
            continue

        # Risk level
        if percent_of_moq >= FRAUD_CRITICAL_THRESHOLD:
            risk_level = "critical"
        elif percent_of_moq >= FRAUD_HIGH_THRESHOLD:
            risk_level = "high"
        else:
            risk_level = "watch"

        # Risk reasons
        risk_reasons = []
        if percent_of_moq >= FRAUD_WATCH_THRESHOLD:
            risk_reasons.append(f"MOQ'nun %{round(percent_of_moq * 100, 1)}'ini tek kullanıcı alıyor")
        if int(r.entry_count) > 1:
            risk_reasons.append(f"Aynı kampanyaya {r.entry_count} demand entry bırakılmış")
        if int(r.flagged_count or 0) > 0:
            risk_reasons.append(f"{r.flagged_count} flaglenmiş entry")
        if int(r.removed_count or 0) > 0:
            risk_reasons.append(f"{r.removed_count} silinmiş entry geçmişi")

        user_info = user_map.get(r.user_id, {})
        title = camp.get("title_override") or product_map.get(camp["product_id"], "")

        entries.append({
            "user_id": str(r.user_id),
            "email": user_info.get("email", ""),
            "full_name": user_info.get("full_name"),
            "campaign_id": str(r.campaign_id),
            "campaign_title": title,
            "campaign_moq": moq,
            "campaign_status": camp["status"],
            "user_total_quantity": user_total_qty,
            "percent_of_moq": round(percent_of_moq * 100, 1),
            "entry_count": int(r.entry_count),
            "flagged_count": int(r.flagged_count or 0),
            "removed_count": int(r.removed_count or 0),
            "last_activity": r.last_activity.isoformat() if r.last_activity else None,
            "risk_level": risk_level,
            "risk_reasons": risk_reasons,
        })

    # Sort by percent_of_moq desc
    entries.sort(key=lambda x: x["percent_of_moq"], reverse=True)

    return {
        "entries": entries,
        "total": len(entries),
        "threshold_pct": int(FRAUD_WATCH_THRESHOLD * 100),
    }


# ══════════════════════════════════════════════════════════════════════════
# ACTION ITEMS — operasyonel aksiyon bekleyen kampanyalar & trendler
# ══════════════════════════════════════════════════════════════════════════

@router.get("/action-items")
async def get_action_items(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Aksiyon bekleyen kampanyalar, trendler ve son moderasyon aktiviteleri.
    """
    now = datetime.now(timezone.utc)
    twenty_four_h_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)

    # 1) MOQ dolmuş ama payment_collecting'e geçmemiş
    moq_stalled_result = await db.execute(
        select(Campaign.id, Campaign.moq_reached_at, Campaign.product_id, Campaign.title_override, Campaign.moq)
        .where(Campaign.status == "moq_reached")
        .order_by(Campaign.moq_reached_at.asc().nullslast())
        .limit(10)
    )
    moq_stalled_rows = moq_stalled_result.all()

    # 2) Ödeme bekleyen (payment_collecting) kampanyalar
    payment_pending_result = await db.execute(
        select(Campaign.id, Campaign.payment_deadline, Campaign.product_id, Campaign.title_override, Campaign.moq)
        .where(Campaign.status == "payment_collecting")
        .order_by(Campaign.payment_deadline.asc().nullslast())
        .limit(10)
    )
    payment_pending_rows = payment_pending_result.all()

    # 3) MOQ'ya en yakın aktif kampanyalar
    # participant toplamı yüksek olanlar
    participant_counts = await db.execute(
        select(
            CampaignParticipant.campaign_id,
            func.sum(CampaignParticipant.quantity).label("total_qty"),
        )
        .where(CampaignParticipant.status.in_(["joined", "invited", "paid"]))
        .group_by(CampaignParticipant.campaign_id)
    )
    part_map = {str(r.campaign_id): int(r.total_qty or 0) for r in participant_counts.all()}

    active_camps_result = await db.execute(
        select(Campaign.id, Campaign.moq, Campaign.product_id, Campaign.title_override)
        .where(Campaign.status == "active")
        .limit(50)
    )
    active_camps = active_camps_result.all()

    # calculate fill pct
    near_moq = []
    for c in active_camps:
        qty = part_map.get(str(c.id), 0)
        if c.moq and c.moq > 0:
            pct = qty / c.moq * 100
            near_moq.append({"campaign_id": str(c.id), "fill_pct": round(pct, 1), "current_qty": qty, "moq": c.moq, "product_id": str(c.product_id), "title_override": c.title_override})
    near_moq.sort(key=lambda x: x["fill_pct"], reverse=True)
    near_moq = near_moq[:10]

    # 4) Son 24 saatte demand alan kampanyalar
    trending_result = await db.execute(
        select(
            CampaignDemandEntry.campaign_id,
            func.count(CampaignDemandEntry.id).label("entry_count"),
            func.sum(CampaignDemandEntry.quantity).label("qty_sum"),
        )
        .where(
            CampaignDemandEntry.created_at >= twenty_four_h_ago,
            CampaignDemandEntry.status == "active",
        )
        .group_by(CampaignDemandEntry.campaign_id)
        .order_by(func.sum(CampaignDemandEntry.quantity).desc())
        .limit(10)
    )
    trending_rows = trending_result.all()

    # 5) Son 30 günde en çok talep alan kampanyalar
    top_demand_30d_result = await db.execute(
        select(
            CampaignDemandEntry.campaign_id,
            func.sum(CampaignDemandEntry.quantity).label("qty_sum"),
        )
        .where(
            CampaignDemandEntry.created_at >= now - timedelta(days=30),
            CampaignDemandEntry.status == "active",
        )
        .group_by(CampaignDemandEntry.campaign_id)
        .order_by(func.sum(CampaignDemandEntry.quantity).desc())
        .limit(10)
    )
    top_demand_30d = top_demand_30d_result.all()

    # 6) Son silinen / flaglenen demand entries
    recent_moderated_result = await db.execute(
        select(CampaignDemandEntry, User)
        .join(User, CampaignDemandEntry.user_id == User.id)
        .where(CampaignDemandEntry.status.in_(["removed", "flagged"]))
        .order_by(CampaignDemandEntry.removed_at.desc().nullslast(),
                  CampaignDemandEntry.created_at.desc())
        .limit(10)
    )
    recent_moderated = recent_moderated_result.all()

    unique_camp_ids_uuid = list({r.id for r in moq_stalled_rows} |
                                 {r.id for r in payment_pending_rows} |
                                 {c.id for c in active_camps} |
                                 {r.campaign_id for r in trending_rows} |
                                 {r.campaign_id for r in top_demand_30d} |
                                 {e.campaign_id for e, _ in recent_moderated})

    if unique_camp_ids_uuid:
        camps_lookup_result = await db.execute(
            select(Campaign.id, Campaign.title_override, Campaign.product_id, Campaign.status)
            .where(Campaign.id.in_(unique_camp_ids_uuid))
        )
        camps_lookup = {c.id: c for c in camps_lookup_result.all()}

        prod_ids_lookup = list({c.product_id for c in camps_lookup.values()})
        if prod_ids_lookup:
            prods_result = await db.execute(
                select(Product.id, Product.title).where(Product.id.in_(prod_ids_lookup))
            )
            prod_map2 = {p.id: p.title for p in prods_result.all()}
        else:
            prod_map2 = {}
    else:
        camps_lookup = {}
        prod_map2 = {}

    def camp_title(cid):
        c = camps_lookup.get(cid)
        if not c:
            return str(cid)
        return c.title_override or prod_map2.get(c.product_id, str(cid))

    return {
        "moq_stalled": [
            {
                "campaign_id": str(r.id),
                "title": camp_title(r.id),
                "moq": r.moq,
                "moq_reached_at": r.moq_reached_at.isoformat() if r.moq_reached_at else None,
            }
            for r in moq_stalled_rows
        ],
        "payment_collecting": [
            {
                "campaign_id": str(r.id),
                "title": camp_title(r.id),
                "moq": r.moq,
                "payment_deadline": r.payment_deadline.isoformat() if r.payment_deadline else None,
            }
            for r in payment_pending_rows
        ],
        "near_moq_active": [
            {
                "campaign_id": x["campaign_id"],
                "title": x["title_override"] or prod_map2.get(
                    next((c.product_id for c in active_camps if str(c.id) == x["campaign_id"]), None),
                    x["campaign_id"]
                ),
                "fill_pct": x["fill_pct"],
                "current_qty": x["current_qty"],
                "moq": x["moq"],
            }
            for x in near_moq
        ],
        "trending_24h": [
            {
                "campaign_id": str(r.campaign_id),
                "title": camp_title(r.campaign_id),
                "entry_count": int(r.entry_count),
                "qty_sum": int(r.qty_sum or 0),
            }
            for r in trending_rows
        ],
        "top_demand_30d": [
            {
                "campaign_id": str(r.campaign_id),
                "title": camp_title(r.campaign_id),
                "qty_sum": int(r.qty_sum or 0),
            }
            for r in top_demand_30d
        ],
        "recent_moderated": [
            {
                "entry_id": str(entry.id),
                "campaign_id": str(entry.campaign_id),
                "campaign_title": camp_title(entry.campaign_id),
                "user_email": user.email,
                "quantity": entry.quantity,
                "status": entry.status,
                "admin_note": entry.admin_note,
                "removal_reason": entry.removal_reason,
                "removed_at": entry.removed_at.isoformat() if entry.removed_at else None,
                "created_at": entry.created_at.isoformat(),
            }
            for entry, user in recent_moderated
        ],
    }


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
