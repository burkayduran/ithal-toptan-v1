"""
Wishlist endpoints – Add/remove from wishlist, MoQ tracking.

Design notes (P0 fixes applied)
────────────────────────────────
* wishlist/add uses a true PostgreSQL UPSERT (INSERT … ON CONFLICT DO UPDATE)
  so that concurrent calls for the same (user, request_id) pair are handled
  atomically by the DB, with no SELECT-then-INSERT race and no exception-driven
  control flow.
* After every write, sync_counter_from_db() is called to recalculate the
  canonical DB count, write it to Redis, and publish it to the SSE channel.
  This is the self-healing mechanism that prevents DB ≠ Redis drift.
* check_and_trigger() uses an atomic UPDATE WHERE status='active' guard so
  the active→moq_reached transition is performed at most once.
* Returns a full WishlistResponse (HTTP 200) on success.
"""
import logging
from typing import List
from uuid import UUID

import redis.asyncio as aioredis
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import (
    Notification,
    ProductRequest,
    SupplierOffer,
    User,
    WishlistEntry,
)
from app.schemas.schemas import WishlistAdd, WishlistResponse
from app.services.moq_service import MoQService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Redis dependency ───────────────────────────────────────────────────────────

async def get_redis() -> aioredis.Redis:
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


# ── helper: build WishlistResponse ────────────────────────────────────────────

async def _build_response(
    db: AsyncSession,
    entry: WishlistEntry,
    product: ProductRequest,
) -> WishlistResponse:
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == product.id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()
    return WishlistResponse(
        id=entry.id,
        request_id=entry.request_id,
        user_id=entry.user_id,
        quantity=entry.quantity,
        status=entry.status,
        joined_at=entry.joined_at,
        notified_at=entry.notified_at,
        payment_deadline=entry.payment_deadline,
        product_title=product.title,
        product_image=product.images[0] if product.images else None,
        selling_price_try=(
            float(offer.selling_price_try)
            if offer and offer.selling_price_try
            else None
        ),
    )


# ── POST /add ─────────────────────────────────────────────────────────────────

@router.post("/add", response_model=WishlistResponse)
@limiter.limit(settings.RATE_LIMIT_WISHLIST_ADD)
async def add_to_wishlist(
    request: Request,
    data: WishlistAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> WishlistResponse:
    """
    Add a product to the wishlist, or update the quantity if already present.

    Semantics: set quantity to N (idempotent).
    Always returns HTTP 200 with a WishlistResponse.
    All concurrency is handled by the DB UPSERT; no exception-driven paths.
    """
    # 1. Validate product
    product_result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == data.request_id)
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.status not in ("active", "moq_reached"):
        raise HTTPException(
            status_code=400,
            detail="This product is not accepting wishlists at the moment",
        )

    # 2. Read existing entry (informational – used for delta logging & status check)
    # This SELECT is NOT the authoritative write; the UPSERT below is.
    existing_result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.request_id == data.request_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    is_new = existing is None
    old_quantity = existing.quantity if existing else 0
    was_waiting = existing.status == "waiting" if existing else False

    # 3. Compute initial status / deadline
    if product.status == "moq_reached":
        upsert_status = "notified"
        upsert_notified_at = product.moq_reached_at
        upsert_deadline = product.payment_deadline
    else:
        upsert_status = "waiting"
        upsert_notified_at = None
        upsert_deadline = None

    # 4. UPSERT — single atomic write, handles all concurrent callers
    t = WishlistEntry.__table__
    insert_stmt = pg_insert(t).values(
        request_id=data.request_id,
        user_id=current_user.id,
        quantity=data.quantity,
        status=upsert_status,
        notified_at=upsert_notified_at,
        payment_deadline=upsert_deadline,
    )
    upsert_stmt = insert_stmt.on_conflict_do_update(
        constraint="uq_wishlist_user_request",
        set_={
            # Always overwrite quantity (set-semantics)
            "quantity": insert_stmt.excluded.quantity,
            # Only transition status waiting->notified; never regress
            "status": sa.case(
                (t.c.status == "waiting", insert_stmt.excluded.status),
                else_=t.c.status,
            ),
            # Only set notified_at / deadline on first notification
            "notified_at": sa.case(
                (t.c.status == "waiting", insert_stmt.excluded.notified_at),
                else_=t.c.notified_at,
            ),
            "payment_deadline": sa.case(
                (t.c.status == "waiting", insert_stmt.excluded.payment_deadline),
                else_=t.c.payment_deadline,
            ),
        },
    ).returning(t)

    upsert_result = await db.execute(upsert_stmt)
    row = upsert_result.fetchone()
    await db.commit()

    # 5. Canonical DB->Redis sync (self-healing)
    moq_service = MoQService(db, redis)
    db_total = await moq_service.sync_counter_from_db(data.request_id)

    logger.info(
        "wishlist/add user_id=%s request_id=%s new_qty=%d old_qty=%d delta=%+d "
        "db_total=%d is_new=%s",
        current_user.id,
        data.request_id,
        data.quantity,
        old_quantity,
        data.quantity - old_quantity,
        db_total,
        is_new,
    )

    # 6. Email notification dedup
    # Trigger when this call created a new notified entry or flipped waiting->notified
    just_notified = upsert_status == "notified" and (is_new or was_waiting)

    if just_notified:
        # ON CONFLICT DO NOTHING guarantees exactly one notification row per
        # (user, request, type) even under heavy concurrency.
        notif_insert = pg_insert(Notification.__table__).values(
            user_id=current_user.id,
            request_id=data.request_id,
            type="moq_reached",
            channel="email",
            subject="Sipariş hazır! 48 saat içinde ödeme yapın",
            status="pending",
        ).on_conflict_do_nothing(constraint="uq_notification_user_request_type")
        notif_result = await db.execute(notif_insert)
        await db.commit()

        # Only the request that inserted the notification enqueues the email task
        if notif_result.rowcount and notif_result.rowcount > 0:
            from app.tasks.email_tasks import send_moq_reached_email
            send_moq_reached_email.delay(
                str(data.request_id),
                upsert_deadline.isoformat() if upsert_deadline else "",
            )

    # 7. Check / trigger MoQ (only while product is still active)
    if product.status == "active":
        outcome = await moq_service.check_and_trigger(data.request_id)
        logger.info(
            "check_and_trigger request_id=%s threshold_met=%s "
            "transition_performed=%s status_after=%s",
            data.request_id,
            outcome.threshold_met,
            outcome.transition_performed,
            outcome.status_after,
        )

    # 8. Reload ORM entry for response building
    entry_result = await db.execute(
        select(WishlistEntry).where(WishlistEntry.id == row.id)
    )
    entry = entry_result.scalar_one()
    product_result2 = await db.execute(
        select(ProductRequest).where(ProductRequest.id == data.request_id)
    )
    product_refreshed = product_result2.scalar_one()

    return await _build_response(db, entry, product_refreshed)


# ── DELETE /{request_id} ──────────────────────────────────────────────────────

@router.delete("/{request_id}")
async def remove_from_wishlist(
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Remove a product from the wishlist."""
    result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.request_id == request_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Not in wishlist")
    if entry.status not in ("waiting", "expired"):
        raise HTTPException(
            status_code=400,
            detail="Cannot remove from wishlist at this stage",
        )

    await db.delete(entry)
    await db.commit()

    # Canonical sync after removal
    moq_service = MoQService(db, redis)
    await moq_service.sync_counter_from_db(request_id)

    return {"message": "Removed from wishlist"}


# ── GET /my ───────────────────────────────────────────────────────────────────

@router.get("/my", response_model=List[WishlistResponse])
async def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the current user's wishlist."""
    result = await db.execute(
        select(WishlistEntry, ProductRequest)
        .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
        .where(WishlistEntry.user_id == current_user.id)
        .order_by(WishlistEntry.joined_at.desc())
    )
    items: List[WishlistResponse] = []
    for entry, product in result.all():
        items.append(await _build_response(db, entry, product))
    return items


# ── GET /progress/{request_id} ────────────────────────────────────────────────

@router.get("/progress/{request_id}")
async def get_moq_progress(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Return current MoQ progress for a product."""
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="No active offer for this product")

    moq_service = MoQService(db, redis)
    current = await moq_service.get_current_count(request_id)

    return {
        "request_id": str(request_id),
        "current": current,
        "target": offer.moq,
        "percentage": round(current / offer.moq * 100, 1) if offer.moq > 0 else 0,
        "selling_price_try": (
            float(offer.selling_price_try) if offer.selling_price_try else None
        ),
    }
