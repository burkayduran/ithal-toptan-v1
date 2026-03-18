"""
Payment endpoints — wishlist-entry–based payment view and confirmation.
Provider integration (iyzico) is out of scope; this layer handles persistence.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.session import get_db
from app.models.models import Payment, ProductRequest, SupplierOffer, User, WishlistEntry
from app.schemas.schemas import PaymentEntryResponse, PaymentInitiateRequest

router = APIRouter()


def _derive_stage(entry_status: str, product_status: str) -> str:
    """Map WishlistEntry status + ProductRequest status to a frontend PaymentStage string."""
    if entry_status == "paid":
        if product_status == "delivered":
            return "delivered"
        if product_status == "ordered":
            return "order_placed"
        return "payment_confirmed"
    if entry_status == "notified":
        return "moq_reached"
    return "campaign_active"


async def _entry_to_response(entry: WishlistEntry, db: AsyncSession) -> PaymentEntryResponse:
    """Build a PaymentEntryResponse from a WishlistEntry."""
    product_result = await db.execute(
        select(ProductRequest).where(ProductRequest.id == entry.request_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == entry.request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()
    selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else 0.0

    return PaymentEntryResponse(
        id=entry.id,
        request_id=entry.request_id,
        product_title=product.title,
        product_image=product.images[0] if product.images else None,
        quantity=entry.quantity,
        total_amount=round(entry.quantity * selling_price, 2),
        status=entry.status,
        payment_deadline=entry.payment_deadline,
        stage=_derive_stage(entry.status, product.status),
        lead_time_days=offer.lead_time_days if offer else None,
    )


@router.get("/entry/{entry_id}", response_model=PaymentEntryResponse)
async def get_payment_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get payment/status view for a wishlist entry.
    Used by both the payment page and the status page.
    """
    result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.id == entry_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return await _entry_to_response(entry, db)


@router.post("/initiate", response_model=PaymentEntryResponse)
async def initiate_payment(
    data: PaymentInitiateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a Payment record for a wishlist entry.
    Entry must belong to the current user.
    """
    result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.id == data.entry_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if entry.status != "notified":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot initiate payment: entry must be in 'notified' state (current: '{entry.status}')",
        )

    # Compute amount
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == entry.request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()
    selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else 0.0
    amount_try = round(entry.quantity * selling_price, 2)

    # Idempotent: skip if Payment already exists
    existing_result = await db.execute(
        select(Payment).where(Payment.wishlist_entry_id == entry.id)
    )
    if not existing_result.scalar_one_or_none():
        payment = Payment(
            wishlist_entry_id=entry.id,
            user_id=current_user.id,
            request_id=entry.request_id,
            amount_try=amount_try,
            quantity=entry.quantity,
            status="pending",
        )
        db.add(payment)
        await db.commit()

    return await _entry_to_response(entry, db)


@router.post("/entry/{entry_id}/confirm", response_model=PaymentEntryResponse)
async def confirm_payment(
    entry_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm (mock) payment for a wishlist entry.
    Sets WishlistEntry.status → 'paid' and Payment.status → 'success'.
    Real provider callback would call this via a webhook instead.
    """
    result = await db.execute(
        select(WishlistEntry).where(
            WishlistEntry.id == entry_id,
            WishlistEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if entry.status != "notified":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm payment: entry must be in 'notified' state (current: '{entry.status}')",
        )

    # Compute amount for Payment record creation
    offer_result = await db.execute(
        select(SupplierOffer).where(
            SupplierOffer.request_id == entry.request_id,
            SupplierOffer.is_selected == True,
        )
    )
    offer = offer_result.scalar_one_or_none()
    selling_price = float(offer.selling_price_try) if offer and offer.selling_price_try else 0.0
    amount_try = round(entry.quantity * selling_price, 2)

    # A7: Check price consistency — if existing payment amount differs from
    # the current offer price, reject to prevent stale-price payments
    payment_result = await db.execute(
        select(Payment).where(Payment.wishlist_entry_id == entry_id)
    )
    payment = payment_result.scalar_one_or_none()

    expected_amount = round(entry.quantity * selling_price, 2)
    if payment and abs(float(payment.amount_try) - expected_amount) > 0.01:
        raise HTTPException(
            status_code=409,
            detail="Fiyat değişmiş. Lütfen sayfayı yenileyip tekrar deneyin.",
        )

    now = datetime.now(timezone.utc)
    entry.status = "paid"
    entry.paid_at = now

    # Ensure Payment record exists — create if initiate was skipped
    if payment:
        payment.status = "success"
        payment.paid_at = now
    else:
        payment = Payment(
            wishlist_entry_id=entry.id,
            user_id=current_user.id,
            request_id=entry.request_id,
            amount_try=amount_try,
            quantity=entry.quantity,
            status="success",
            paid_at=now,
        )
        db.add(payment)

    await db.commit()
    await db.refresh(entry)

    # Trigger payment success email
    from app.tasks.email_tasks import send_payment_success_email
    send_payment_success_email.delay(str(entry_id))

    return await _entry_to_response(entry, db)
