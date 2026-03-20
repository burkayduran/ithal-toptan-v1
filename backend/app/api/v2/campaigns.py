"""
V2 Campaign endpoints — public + user.
Primary source: campaigns + products tables.
"""
from datetime import datetime, timezone
from math import ceil
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import (
    Campaign, CampaignParticipant, Product, User,
)
from app.schemas.v2_schemas import (
    CampaignProgress,
    CampaignResponse,
    JoinCampaignPayload,
    PaginatedCampaignResponse,
    ParticipantResponse,
)

router = APIRouter()

# Statuses visible to public
_PUBLIC_STATUSES = {"active", "moq_reached", "payment_collecting"}
_DETAIL_STATUSES = {"active", "moq_reached", "payment_collecting", "ordered", "delivered"}


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
# PUBLIC ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@router.get("", response_model=PaginatedCampaignResponse)
async def list_campaigns(
    category_id: Optional[UUID] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List active campaigns (public)."""
    base_filter = Campaign.status.in_(list(_PUBLIC_STATUSES))

    # Count query
    count_query = (
        select(func.count(Campaign.id))
        .join(Product, Campaign.product_id == Product.id)
        .where(base_filter)
    )
    # Data query
    query = (
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(base_filter)
    )

    if category_id:
        count_query = count_query.where(Product.category_id == category_id)
        query = query.where(Product.category_id == category_id)

    if search:
        search_filter = or_(
            Product.title.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
            Campaign.title_override.ilike(f"%{search}%"),
        )
        count_query = count_query.where(search_filter)
        query = query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Campaign.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return PaginatedCampaignResponse(
            items=[], total=total, page=page, per_page=per_page, total_pages=0,
        )

    # Batch participant counts
    campaign_ids = [campaign.id for campaign, _ in rows]
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

    items = []
    for campaign, product in rows:
        count = counts_map.get(campaign.id, 0)
        items.append(_build_campaign_response(campaign, product, count))

    return PaginatedCampaignResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total > 0 else 0,
    )


# ── /my MUST be before /{campaign_id} to avoid route collision ────────────

@router.get("/my", response_model=List[ParticipantResponse])
async def get_my_campaigns(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List current user's campaign participations."""
    result = await db.execute(
        select(CampaignParticipant, Campaign, Product)
        .join(Campaign, CampaignParticipant.campaign_id == Campaign.id)
        .join(Product, Campaign.product_id == Product.id)
        .where(CampaignParticipant.user_id == current_user.id)
        .order_by(CampaignParticipant.joined_at.desc())
    )
    rows = result.all()

    if not rows:
        return []

    # Batch participant counts for moq_fill_percentage
    campaign_ids = [campaign.id for _, campaign, _ in rows]
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

    items = []
    for participant, campaign, product in rows:
        title = campaign.title_override or product.title
        images = campaign.images_override or product.images or []
        selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else None
        moq = campaign.moq or 0
        count = counts_map.get(campaign.id, 0)

        items.append(ParticipantResponse(
            id=participant.id,
            campaign_id=campaign.id,
            user_id=participant.user_id,
            quantity=participant.quantity,
            status=participant.status,
            campaign_title=title,
            campaign_image=images[0] if images else None,
            campaign_status=campaign.status,
            selling_price_try=selling_price,
            total_amount=round(participant.quantity * selling_price, 2) if selling_price else None,
            moq_fill_percentage=round(count / moq * 100, 1) if moq else None,
            joined_at=participant.joined_at,
            invited_at=participant.invited_at,
            payment_deadline=participant.payment_deadline,
            paid_at=participant.paid_at,
        ))

    return items


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get campaign detail (public)."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row
    if campaign.status not in _DETAIL_STATUSES:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Atomic view_count increment
    await db.execute(
        update(Campaign)
        .where(Campaign.id == campaign_id)
        .values(view_count=Campaign.view_count + 1)
    )
    await db.commit()
    current_view_count = campaign.view_count + 1

    # Participant count
    count_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
        .where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
    )
    participant_count = int(count_result.scalar() or 0)

    resp = _build_campaign_response(campaign, product, participant_count)
    resp.view_count = current_view_count
    return resp


@router.get("/{campaign_id}/similar", response_model=List[CampaignResponse])
async def get_similar_campaigns(
    campaign_id: UUID,
    limit: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Similar campaigns in same category."""
    # Get source campaign's category
    source = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    source_row = source.one_or_none()
    if not source_row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    _, source_product = source_row
    category_id = source_product.category_id

    query = (
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(
            Campaign.id != campaign_id,
            Campaign.status.in_(list(_PUBLIC_STATUSES)),
        )
    )
    if category_id:
        query = query.where(Product.category_id == category_id)

    query = query.order_by(Campaign.created_at.desc()).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return []

    # Batch counts
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


@router.get("/{campaign_id}/progress", response_model=CampaignProgress)
@limiter.limit("60/minute")
async def get_campaign_progress(
    request: Request,
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """MoQ progress for a campaign (public, rate-limited)."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()

    if not campaign or campaign.status not in _PUBLIC_STATUSES:
        raise HTTPException(status_code=404, detail="Not found")

    count_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
        .where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
    )
    current = int(count_result.scalar() or 0)
    moq = campaign.moq or 0

    return CampaignProgress(
        campaign_id=campaign.id,
        current=current,
        target=moq,
        percentage=round(current / moq * 100, 1) if moq else 0,
        selling_price_try=float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else None,
    )


# ══════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS (AUTH REQUIRED)
# ══════════════════════════════════════════════════════════════════════════

@router.post("/{campaign_id}/join", response_model=ParticipantResponse)
async def join_campaign(
    campaign_id: UUID,
    data: JoinCampaignPayload,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a campaign (add to participant list)."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row

    if campaign.status not in ("active", "moq_reached"):
        raise HTTPException(
            status_code=400,
            detail="This campaign is not accepting participants at the moment",
        )

    # Check existing participant
    existing_result = await db.execute(
        select(CampaignParticipant).where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.user_id == current_user.id,
        )
    )
    participant = existing_result.scalar_one_or_none()

    selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else None

    if participant:
        # Update quantity
        participant.quantity = data.quantity
    else:
        # Determine initial status
        if campaign.status == "moq_reached":
            initial_status = "invited"
            invited_at = campaign.moq_reached_at
            deadline = campaign.payment_deadline
        else:
            initial_status = "joined"
            invited_at = None
            deadline = None

        participant = CampaignParticipant(
            campaign_id=campaign_id,
            user_id=current_user.id,
            quantity=data.quantity,
            status=initial_status,
            unit_price_try_snapshot=selling_price,
            total_amount_try_snapshot=round(data.quantity * selling_price, 2) if selling_price else None,
            invited_at=invited_at,
            payment_deadline=deadline,
        )
        db.add(participant)
        await db.flush()

    await db.commit()
    await db.refresh(participant)

    # Build response
    moq = campaign.moq or 0
    count_result = await db.execute(
        select(func.coalesce(func.sum(CampaignParticipant.quantity), 0))
        .where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.status.in_(["joined", "invited"]),
        )
    )
    p_count = int(count_result.scalar() or 0)

    title = campaign.title_override or product.title
    images = campaign.images_override or product.images or []

    return ParticipantResponse(
        id=participant.id,
        campaign_id=campaign.id,
        user_id=participant.user_id,
        quantity=participant.quantity,
        status=participant.status,
        campaign_title=title,
        campaign_image=images[0] if images else None,
        campaign_status=campaign.status,
        selling_price_try=selling_price,
        total_amount=round(participant.quantity * selling_price, 2) if selling_price else None,
        moq_fill_percentage=round(p_count / moq * 100, 1) if moq else None,
        joined_at=participant.joined_at,
        invited_at=participant.invited_at,
        payment_deadline=participant.payment_deadline,
        paid_at=participant.paid_at,
    )


@router.delete("/{campaign_id}/leave")
async def leave_campaign(
    campaign_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Leave a campaign. Only allowed in joined or expired status."""
    result = await db.execute(
        select(CampaignParticipant).where(
            CampaignParticipant.campaign_id == campaign_id,
            CampaignParticipant.user_id == current_user.id,
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        raise HTTPException(status_code=404, detail="Not in this campaign")

    if participant.status not in ("joined", "expired"):
        raise HTTPException(
            status_code=400,
            detail="Cannot leave campaign at this stage",
        )

    await db.delete(participant)
    await db.commit()

    return {"message": "Left campaign successfully"}
