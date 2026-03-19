"""
Wishlist endpoints - Add/remove from wishlist, MoQ tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID
import redis.asyncio as aioredis

from app.db.session import get_db
from app.models.models import User, ProductRequest, WishlistEntry, SupplierOffer, Notification
from app.schemas.schemas import WishlistAdd, WishlistResponse
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.core.limiter import limiter
from app.core.redis import get_redis
from app.services.moq_service import MoQService

# Statuses that may expose progress data to the public
_PROGRESS_ALLOWED_STATUSES = {"active", "moq_reached", "payment_collecting"}

router = APIRouter()


async def _create_moq_notification_if_missing(
    db: AsyncSession,
    user_id: UUID,
    request_id: UUID,
) -> bool:
    """Create a single moq_reached notification if none exists yet."""
    existing_result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.request_id == request_id,
            Notification.type == "moq_reached",
            Notification.channel == "email",
            Notification.status.in_(["pending", "sent", "delivered", "opened", "clicked"]),
        )
    )
    if existing_result.first():
        return False

    db.add(
        Notification(
            user_id=user_id,
            request_id=request_id,
            type="moq_reached",
            channel="email",
            subject="Sipariş hazır! 48 saat içinde ödeme yapın",
            status="pending",
        )
    )
    return True


@router.post("/add", response_model=WishlistResponse)
async def add_to_wishlist(
    data: WishlistAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Add product to wishlist (UPSERT-safe, idempotent)."""
    product_result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == data.request_id)
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if product.status not in ["active", "moq_reached"]:
        raise HTTPException(status_code=400, detail="This product is not accepting wishlists at the moment")

    existing_result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.request_id == data.request_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if product.status == "moq_reached":
        initial_status = "notified"
        initial_deadline = product.payment_deadline
        initial_notified_at = product.moq_reached_at
    else:
        initial_status = "waiting"
        initial_deadline = None
        initial_notified_at = None

    upsert_stmt = (
        insert(WishlistEntry)
        .values(
            request_id=data.request_id,
            user_id=current_user.id,
            quantity=data.quantity,
            status=initial_status,
            notified_at=initial_notified_at,
            payment_deadline=initial_deadline,
        )
        .on_conflict_do_update(
            index_elements=[WishlistEntry.request_id, WishlistEntry.user_id],
            set_={"quantity": data.quantity},
        )
    )

    should_notify = False
    try:
        await db.execute(upsert_stmt)

        if product.status == "moq_reached":
            transition_result = await db.execute(
                WishlistEntry.__table__.update()
                .where(
                    WishlistEntry.request_id == data.request_id,
                    WishlistEntry.user_id == current_user.id,
                    WishlistEntry.status == "waiting",
                )
                .values(
                    status="notified",
                    notified_at=initial_notified_at,
                    payment_deadline=initial_deadline,
                )
            )
            should_notify = transition_result.rowcount > 0 or existing is None
            if should_notify:
                await _create_moq_notification_if_missing(db, current_user.id, data.request_id)

        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Wishlist update conflict, please retry")

    # Dual-write: shadow join (fire-and-forget, separate mini-commit)
    try:
        from app.services.dual_write_service import DualWriteService
        dw = DualWriteService(db)

        offer_for_dw = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == data.request_id,
                SupplierOffer.is_selected == True,
            )
        )
        dw_offer = offer_for_dw.scalar_one_or_none()
        dw_selling_price = float(dw_offer.selling_price_try) if dw_offer and dw_offer.selling_price_try else None

        # Re-fetch entry to get its id
        entry_result_dw = await db.execute(
            select(WishlistEntry).where(
                WishlistEntry.request_id == data.request_id,
                WishlistEntry.user_id == current_user.id,
            )
        )
        entry_dw = entry_result_dw.scalar_one_or_none()

        if entry_dw:
            await dw.shadow_join_wishlist(
                legacy_request_id=data.request_id,
                legacy_entry_id=entry_dw.id,
                user_id=current_user.id,
                quantity=data.quantity,
                status=entry_dw.status,
                selling_price_try=dw_selling_price,
            )
            await db.commit()
    except Exception:
        import logging
        logging.getLogger("dual_write").exception("shadow_join_wishlist endpoint failed")

    # Side effects run only after a successful commit
    moq_service = MoQService(db, redis)
    await moq_service.sync_counter_from_db(data.request_id)

    if should_notify:
        from app.tasks.email_tasks import send_moq_reached_email

        send_moq_reached_email.delay(
            str(data.request_id),
            initial_deadline.isoformat() if initial_deadline else "",
        )

    if product.status == "active":
        await moq_service.check_and_trigger(data.request_id)

    row_result = await db.execute(
        select(WishlistEntry, ProductRequest)
        .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
        .where(
            WishlistEntry.request_id == data.request_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    entry, product_row = row_result.one()

    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == data.request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()

    selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else None
    return WishlistResponse(
        id=entry.id,
        request_id=entry.request_id,
        user_id=entry.user_id,
        quantity=entry.quantity,
        status=entry.status,
        joined_at=entry.joined_at,
        notified_at=entry.notified_at,
        payment_deadline=entry.payment_deadline,
        product_title=product_row.title,
        product_image=product_row.images[0] if product_row.images else None,
        selling_price_try=selling_price,
        total_amount=round(entry.quantity * selling_price, 2) if selling_price is not None else None,
    )


@router.get("/my", response_model=List[WishlistResponse])
async def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's wishlist with computed total_amount and moq_fill_percentage."""
    result = await db.execute(
        select(WishlistEntry, ProductRequest)
        .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
        .where(WishlistEntry.user_id == current_user.id)
        .order_by(WishlistEntry.joined_at.desc())
    )
    rows = result.all()

    if not rows:
        return []

    # Single aggregation query — avoids N Redis calls for moq fill percentage
    request_ids = [product.id for _, product in rows]
    count_result = await db.execute(
        select(WishlistEntry.request_id, func.sum(WishlistEntry.quantity))
        .where(
            WishlistEntry.request_id.in_(request_ids),
            WishlistEntry.status.in_(["waiting", "notified"]),
        )
        .group_by(WishlistEntry.request_id)
    )
    wishlist_counts: dict = {row[0]: int(row[1]) for row in count_result.all()}

    # Batch: offers for all products in wishlist
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id.in_(request_ids),
            SupplierOffer.is_selected == True
        )
    )
    offers_map = {o.request_id: o for o in offer_result.scalars().all()}

    items = []
    for entry, product in rows:
        offer = offers_map.get(product.id)

        selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else None
        moq = offer.moq if offer and offer.moq else None
        current_count = wishlist_counts.get(product.id, 0)

        items.append(WishlistResponse(
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
            selling_price_try=selling_price,
            total_amount=round(entry.quantity * selling_price, 2) if selling_price is not None else None,
            moq_fill_percentage=round(min(current_count / moq * 100, 100), 1) if moq else None,
        ))

    return items


@router.delete("/{request_id}")
async def remove_from_wishlist(
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Remove product from wishlist."""
    result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.request_id == request_id,
            WishlistEntry.user_id == current_user.id
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Not in wishlist")

    # Can only remove if waiting or expired
    if entry.status not in ["waiting", "expired"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove from wishlist at this stage"
        )

    await db.delete(entry)
    await db.commit()

    # Re-sync from DB aggregate to avoid Redis drift
    moq_service = MoQService(db, redis)
    await moq_service.sync_counter_from_db(request_id)

    return {"message": "Removed from wishlist"}


@router.get("/progress/{request_id}")
@limiter.limit("60/minute")
async def get_moq_progress(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Get current MoQ progress for a product (public, rate-limited)."""
    # Verify product exists and is publicly discoverable
    product_result = await db.execute(
        select(ProductRequest.status).where(ProductRequest.id == request_id)
    )
    product_status = product_result.scalar_one_or_none()

    if product_status is None or product_status not in _PROGRESS_ALLOWED_STATUSES:
        raise HTTPException(status_code=404, detail="Not found")

    # Get offer
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()

    if not offer:
        raise HTTPException(status_code=404, detail="Not found")

    # Get current count
    moq_service = MoQService(db, redis)
    current = await moq_service.get_current_count(request_id)

    return {
        "request_id": str(request_id),
        "current": current,
        "target": offer.moq,
        "percentage": round(current / offer.moq * 100, 1) if offer.moq else 0,
        "selling_price_try": float(offer.selling_price_try) if offer.selling_price_try else None,
    }
