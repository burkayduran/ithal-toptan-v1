"""
V2 Payment endpoints — participant-based payment view and confirmation.
Primary source: campaign_participants + payment_transactions tables.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_active_user
from app.db.session import get_db
from app.models.models import (
    Campaign, CampaignParticipant, ParticipantStatusHistory,
    PaymentTransaction, Product, User,
)
from app.schemas.v2_schemas import PaymentEntryV2Response

router = APIRouter()


def _derive_stage(participant_status: str, campaign_status: str) -> str:
    """Map participant + campaign status to a frontend stage string."""
    if participant_status == "paid":
        if campaign_status == "delivered":
            return "delivered"
        if campaign_status == "ordered":
            return "order_placed"
        return "payment_confirmed"
    if participant_status == "invited":
        return "moq_reached"
    return "campaign_active"


async def _participant_to_response(
    participant: CampaignParticipant,
    db: AsyncSession,
) -> PaymentEntryV2Response:
    """Build PaymentEntryV2Response from a CampaignParticipant."""
    result = await db.execute(
        select(Campaign, Product)
        .join(Product, Campaign.product_id == Product.id)
        .where(Campaign.id == participant.campaign_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign, product = row

    title = campaign.title_override or product.title
    images = campaign.images_override or product.images or []

    # Prefer participant snapshot (price at join time) over campaign current price
    if participant.total_amount_try_snapshot is not None:
        total_amount = float(participant.total_amount_try_snapshot)
    else:
        selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else 0.0
        total_amount = round(participant.quantity * selling_price, 2)

    return PaymentEntryV2Response(
        id=participant.id,
        campaign_id=campaign.id,
        campaign_title=title,
        campaign_image=images[0] if images else None,
        quantity=participant.quantity,
        total_amount=total_amount,
        status=participant.status,
        payment_deadline=participant.payment_deadline,
        stage=_derive_stage(participant.status, campaign.status),
        lead_time_days=campaign.lead_time_days,
    )


@router.get("/{participant_id}", response_model=PaymentEntryV2Response)
async def get_payment_entry(
    participant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment/status view for a participant."""
    result = await db.execute(
        select(CampaignParticipant).where(
            CampaignParticipant.id == participant_id,
            CampaignParticipant.user_id == current_user.id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return await _participant_to_response(participant, db)


@router.post("/{participant_id}/confirm", response_model=PaymentEntryV2Response)
async def confirm_payment(
    participant_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm (mock) payment for a participant.
    Sets participant status → 'paid' and creates PaymentTransaction.
    """
    result = await db.execute(
        select(CampaignParticipant).where(
            CampaignParticipant.id == participant_id,
            CampaignParticipant.user_id == current_user.id,
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    if participant.status != "invited":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm payment: participant must be in 'invited' state (current: '{participant.status}')",
        )

    # Get campaign for snapshot data
    campaign_result = await db.execute(
        select(Campaign).where(Campaign.id == participant.campaign_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # === DEADLINE GUARD ===
    now = datetime.now(timezone.utc)

    # 1. Payment deadline geçmiş mi?
    if participant.payment_deadline and now > participant.payment_deadline:
        raise HTTPException(
            status_code=400,
            detail="Ödeme süresi dolmuş. Bu kampanya için ödeme artık kabul edilmiyor.",
        )

    # 2. Campaign hâlâ ödeme kabul ediyor mu?
    if campaign.status not in ("moq_reached", "payment_collecting"):
        raise HTTPException(
            status_code=400,
            detail=f"Bu kampanya şu an ödeme kabul etmiyor (durum: '{campaign.status}').",
        )

    # Use participant snapshot price (frozen at join time), fallback to campaign current
    if participant.unit_price_try_snapshot is not None:
        selling_price = float(participant.unit_price_try_snapshot)
    else:
        selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else 0.0

    if participant.total_amount_try_snapshot is not None:
        amount_try = float(participant.total_amount_try_snapshot)
    else:
        amount_try = round(participant.quantity * selling_price, 2)

    # Update participant status
    old_status = participant.status
    participant.status = "paid"
    participant.paid_at = now

    # Status history
    db.add(ParticipantStatusHistory(
        participant_id=participant.id,
        old_status=old_status,
        new_status="paid",
        reason="payment_confirmed",
    ))

    # Create PaymentTransaction
    tx = PaymentTransaction(
        participant_id=participant.id,
        campaign_id=campaign.id,
        user_id=current_user.id,
        amount_try=amount_try,
        quantity=participant.quantity,
        unit_price_try_snapshot=selling_price,
        fx_rate_snapshot=float(campaign.fx_rate_snapshot) if campaign.fx_rate_snapshot else None,
        provider="iyzico",
        status="success",
        completed_at=now,
    )
    db.add(tx)

    await db.commit()
    await db.refresh(participant)

    # Trigger payment success email
    try:
        from app.tasks.email_tasks import send_payment_success_email
        send_payment_success_email.delay(str(participant.id))
    except Exception:
        pass

    return await _participant_to_response(participant, db)
