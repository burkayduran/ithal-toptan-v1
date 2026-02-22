"""
Wishlist endpoints - Add/remove from wishlist, MoQ tracking
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List
from uuid import UUID
import redis.asyncio as aioredis

from app.core.limiter import limiter
from app.db.session import get_db
from app.models.models import User, ProductRequest, WishlistEntry, SupplierOffer, Notification
from app.schemas.schemas import WishlistAdd, WishlistResponse
from app.core.auth import get_current_active_user
from app.core.config import settings
from app.services.moq_service import MoQService

router = APIRouter()


async def get_redis() -> aioredis.Redis:
    """Get Redis connection."""
    redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield redis
    finally:
        await redis.aclose()


@router.post("/add")
@limiter.limit(settings.RATE_LIMIT_WISHLIST_ADD)
async def add_to_wishlist(
    request: Request,
    data: WishlistAdd,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Add product to wishlist."""
    # Check if product exists and is active
    product_result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == data.request_id)
    )
    product = product_result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product.status not in ["active", "moq_reached"]:
        raise HTTPException(
            status_code=400,
            detail="This product is not accepting wishlists at the moment"
        )
    
    # Check if already in wishlist
    existing_result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.request_id == data.request_id,
            WishlistEntry.user_id == current_user.id
        )
    )
    existing = existing_result.scalar_one_or_none()
    
    moq_service = MoQService(db, redis)

    # If the product is already in payment phase, new joiners are immediately notified
    if product.status == "moq_reached":
        initial_status = "notified"
        initial_deadline = product.payment_deadline
        initial_notified_at = product.moq_reached_at
    else:
        initial_status = "waiting"
        initial_deadline = None
        initial_notified_at = None

    if existing:
        # Update quantity
        old_quantity = existing.quantity
        existing.quantity = data.quantity

        # Sync status/deadline if product transitioned to moq_reached since they joined.
        # Track whether notified_at transitions null→now so we send the email exactly once.
        just_notified = False
        if product.status == "moq_reached" and existing.status == "waiting":
            existing.status = "notified"
            existing.notified_at = initial_notified_at
            existing.payment_deadline = initial_deadline
            just_notified = True

        await db.commit()

        # Update Redis counter
        quantity_diff = data.quantity - old_quantity
        if quantity_diff != 0:
            if quantity_diff > 0:
                await moq_service.increment(data.request_id, quantity_diff)
            else:
                await moq_service.decrement(data.request_id, abs(quantity_diff))

        # Only enqueue email if this request is the one that flipped the status.
        # Guards against double-emails from concurrent retries or double-clicks.
        if just_notified:
            notif_check = await db.execute(
                select(Notification).where(
                    Notification.user_id == current_user.id,
                    Notification.request_id == data.request_id,
                    Notification.type == "moq_reached",
                    Notification.status.in_(["pending", "sent"]),
                )
            )
            if notif_check.scalar_one_or_none() is None:
                notification = Notification(
                    user_id=current_user.id,
                    request_id=data.request_id,
                    type="moq_reached",
                    channel="email",
                    subject="Sipariş hazır! 48 saat içinde ödeme yapın",
                    status="pending",
                )
                db.add(notification)
                await db.commit()
                from app.tasks.email_tasks import send_moq_reached_email
                send_moq_reached_email.delay(
                    str(data.request_id),
                    initial_deadline.isoformat() if initial_deadline else "",
                )

        message = "Wishlist updated"
    else:
        # Create new entry with the correct initial status
        entry = WishlistEntry(
            request_id=data.request_id,
            user_id=current_user.id,
            quantity=data.quantity,
            status=initial_status,
            notified_at=initial_notified_at,
            payment_deadline=initial_deadline,
        )
        db.add(entry)
        await db.flush()  # get entry.id before commit

        # If immediately notified, create a notification record only if one doesn't
        # already exist (guards against retries / concurrent requests).
        should_send_email = False
        if initial_status == "notified":
            notif_check = await db.execute(
                select(Notification).where(
                    Notification.user_id == current_user.id,
                    Notification.request_id == data.request_id,
                    Notification.type == "moq_reached",
                    Notification.status.in_(["pending", "sent"]),
                )
            )
            if notif_check.scalar_one_or_none() is None:
                notification = Notification(
                    user_id=current_user.id,
                    request_id=data.request_id,
                    type="moq_reached",
                    channel="email",
                    subject="Sipariş hazır! 48 saat içinde ödeme yapın",
                    status="pending",
                )
                db.add(notification)
                should_send_email = True

        try:
            await db.commit()
        except IntegrityError:
            # Concurrent request already created this row — roll back our attempt
            # and treat the existing row as the target (idempotent "set quantity").
            await db.rollback()

            collision_result = await db.execute(
                select(WishlistEntry).where(
                    WishlistEntry.request_id == data.request_id,
                    WishlistEntry.user_id == current_user.id,
                )
            )
            existing = collision_result.scalar_one_or_none()
            if existing is None:
                # Extremely unlikely — give up gracefully
                raise HTTPException(status_code=500, detail="Wishlist state error, please retry")

            old_quantity = existing.quantity
            existing.quantity = data.quantity
            if product.status == "moq_reached" and existing.status == "waiting":
                existing.status = "notified"
                existing.notified_at = initial_notified_at
                existing.payment_deadline = initial_deadline
            await db.commit()

            quantity_diff = data.quantity - old_quantity
            if quantity_diff > 0:
                await moq_service.increment(data.request_id, quantity_diff)
            elif quantity_diff < 0:
                await moq_service.decrement(data.request_id, abs(quantity_diff))

            if product.status == "active":
                await moq_service.check_and_trigger(data.request_id)

            return {"message": "Wishlist updated"}

        # Increment Redis counter
        await moq_service.increment(data.request_id, data.quantity)

        if should_send_email:
            from app.tasks.email_tasks import send_moq_reached_email
            send_moq_reached_email.delay(
                str(data.request_id),
                initial_deadline.isoformat() if initial_deadline else "",
            )

        message = "Added to wishlist"

    # Only check/trigger MoQ when the product is still in active state
    if product.status == "active":
        await moq_service.check_and_trigger(data.request_id)
    
    return {"message": message}


@router.delete("/{request_id}")
async def remove_from_wishlist(
    request_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
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
    
    quantity = entry.quantity
    
    await db.delete(entry)
    await db.commit()
    
    # Update Redis counter
    moq_service = MoQService(db, redis)
    await moq_service.decrement(request_id, quantity)
    
    return {"message": "Removed from wishlist"}


@router.get("/my", response_model=List[WishlistResponse])
async def get_my_wishlist(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's wishlist."""
    result = await db.execute(
        select(WishlistEntry, ProductRequest)
        .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
        .where(WishlistEntry.user_id == current_user.id)
        .order_by(WishlistEntry.joined_at.desc())
    )
    
    items = []
    for entry, product in result.all():
        # Get offer for pricing
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == product.id,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        item_dict = {
            "id": entry.id,
            "request_id": entry.request_id,
            "user_id": entry.user_id,
            "quantity": entry.quantity,
            "status": entry.status,
            "joined_at": entry.joined_at,
            "notified_at": entry.notified_at,
            "payment_deadline": entry.payment_deadline,
            "product_title": product.title,
            "product_image": product.images[0] if product.images else None,
            "selling_price_try": float(offer.selling_price_try) if offer and offer.selling_price_try else None,
        }
        
        items.append(WishlistResponse(**item_dict))
    
    return items


@router.get("/progress/{request_id}")
async def get_moq_progress(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis)
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
        "percentage": round(current / offer.moq * 100, 1) if offer.moq > 0 else 0,
        "selling_price_try": float(offer.selling_price_try) if offer.selling_price_try else None
    }
