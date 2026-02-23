"""
Wishlist endpoints - Add/remove from wishlist, MoQ tracking
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID
import redis.asyncio as aioredis

from app.db.session import get_db
from app.models.models import User, ProductRequest, WishlistEntry, SupplierOffer, Notification
from app.schemas.schemas import WishlistAdd, WishlistResponse
from app.core.auth import get_current_active_user
from app.services.moq_service import MoQService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_redis_client(request: Request) -> aioredis.Redis:
    """Return the application-wide shared Redis client from app.state.

    The client is created once at startup and reused for every request,
    avoiding per-request connection churn.  Do NOT close it inside endpoints.
    """
    return request.app.state.redis


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
    redis: aioredis.Redis = Depends(get_redis_client),
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
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "IntegrityError on wishlist add — request_id=%s user_id=%s quantity=%s: %s",
            data.request_id,
            current_user.id,
            data.quantity,
            exc,
            exc_info=True,
        )

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
        selling_price_try=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
    )


@router.delete("/{request_id}")
async def remove_from_wishlist(
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
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


@router.get("/my", response_model=List[WishlistResponse])
async def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's wishlist.

    Uses a single JOIN query to fetch wishlist entries, product info, and the
    selected supplier offer in O(1) DB round-trips instead of N+1.
    """
    result = await db.execute(
        select(WishlistEntry, ProductRequest, SupplierOffer)
        .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
        .outerjoin(
            SupplierOffer,
            (SupplierOffer.request_id == WishlistEntry.request_id)
            & (SupplierOffer.is_selected == True),
        )
        .where(WishlistEntry.user_id == current_user.id)
        .order_by(WishlistEntry.joined_at.desc())
    )

    items = []
    for entry, product, offer in result.all():
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
            selling_price_try=float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        ))

    return items


@router.get("/progress/{request_id}")
async def get_moq_progress(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    """Get current MoQ progress for a product."""
    # Get offer
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == request_id,
            SupplierOffer.is_selected == True
        )
    )
    offer = offer_result.scalar_one_or_none()

    if not offer:
        raise HTTPException(status_code=404, detail="No active offer for this product")

    # Get current count
    moq_service = MoQService(db, redis)
    current = await moq_service.get_current_count(request_id)

    return {
        "request_id": str(request_id),
        "current": current,
        "target": offer.moq,
        "percentage": round(current / offer.moq * 100, 1) if offer.moq else 0,
        "selling_price_try": float(offer.selling_price_try) if offer.selling_price_try else None
    }
