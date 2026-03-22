"""
Celery Email Tasks
Background jobs for sending emails.
Primary source: campaigns + campaign_participants tables.
"""
import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_, func
from uuid import UUID

from app.tasks.celery_app import celery_app

logger = logging.getLogger("ithal_toptan")
from app.services.email_service import EmailService
from app.templates.email_templates import EmailTemplates
from app.db.session import AsyncSessionLocal
from app.models.models import (
    User, Campaign, Product, CampaignParticipant, Notification,
)
from app.core.config import settings


@celery_app.task(
    name="app.tasks.email_tasks.send_moq_reached_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_moq_reached_email(campaign_id: str, deadline: str):
    """
    Send MoQ reached email to all invited participants.
    Called when MoQ threshold is reached.

    Args:
        campaign_id: Campaign UUID
        deadline: Payment deadline (ISO format)
    """
    import asyncio
    asyncio.run(_send_moq_reached_email_async(campaign_id, deadline))


async def _send_moq_reached_email_async(campaign_id: str, deadline: str):
    """Async implementation of MoQ reached email."""
    async with AsyncSessionLocal() as db:
        campaign_uuid = UUID(campaign_id)

        # Get campaign + product
        result = await db.execute(
            select(Campaign, Product)
            .join(Product, Campaign.product_id == Product.id)
            .where(Campaign.id == campaign_uuid)
        )
        row = result.one_or_none()

        if not row:
            logger.error("Campaign %s not found", campaign_id)
            return

        campaign, product = row
        title = campaign.title_override or product.title
        selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else 0

        # Get invited participants with user info
        entries_result = await db.execute(
            select(CampaignParticipant, User)
            .join(User, CampaignParticipant.user_id == User.id)
            .where(
                CampaignParticipant.campaign_id == campaign_uuid,
                CampaignParticipant.status == "invited",
            )
        )
        entries = entries_result.all()

        if not entries:
            logger.warning("No invited participants for campaign %s", campaign_id)
            return

        logger.info("Sending MoQ reached emails to %d users", len(entries))

        now = datetime.now(timezone.utc)

        # Send emails
        for participant, user in entries:
            email_data = {
                "product_title": title,
                "quantity": participant.quantity,
                "unit_price": selling_price,
                "total_price": selling_price * participant.quantity,
                "moq": campaign.moq,
                "deadline": datetime.fromisoformat(deadline).strftime("%d.%m.%Y %H:%M"),
                "lead_time_days": campaign.lead_time_days or 30,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{participant.id}"
            }

            html = EmailTemplates.moq_reached(email_data)

            try:
                send_result = EmailService.send_email(
                    to=user.email,
                    subject=f"🎉 {title} için sipariş hazır! 48 saat içinde ödeme yapın",
                    html=html
                )
            except Exception as exc:
                logger.error("Email exception for %s: %s", user.email, exc)
                send_result = {"status": "error", "error": str(exc)}

            # Update notification status based on actual send outcome
            if send_result.get("status") == "skipped":
                notif_status = "skipped"
            elif send_result.get("status") in ("error",):
                notif_status = "failed"
            else:
                notif_status = "sent"

            # Lookup pending notification by campaign_id (primary key)
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.campaign_id == campaign_uuid,
                        Notification.type == "moq_reached",
                        Notification.status == "pending"
                    )
                )
            )
            notification = notif_result.scalar_one_or_none()

            if notification:
                notification.status = notif_status
                # sent_at only set when actually sent
                if notif_status == "sent":
                    notification.sent_at = now

        await db.commit()
        logger.info("Sent %d MoQ reached emails", len(entries))


@celery_app.task(
    name="app.tasks.email_tasks.send_payment_reminders",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_payment_reminders():
    """
    Send payment reminder emails.
    Runs every 6 hours via Celery Beat.
    Sends reminder if < 24 hours remaining.
    """
    import asyncio
    asyncio.run(_send_payment_reminders_async())


async def _send_payment_reminders_async():
    """Async implementation of payment reminders."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        reminder_threshold = now + timedelta(hours=24)

        # Get participants that:
        # - status = invited
        # - deadline < 24 hours
        entries_result = await db.execute(
            select(CampaignParticipant, User, Campaign, Product)
            .join(User, CampaignParticipant.user_id == User.id)
            .join(Campaign, CampaignParticipant.campaign_id == Campaign.id)
            .join(Product, Campaign.product_id == Product.id)
            .where(
                and_(
                    CampaignParticipant.status == "invited",
                    CampaignParticipant.payment_deadline.isnot(None),
                    CampaignParticipant.payment_deadline < reminder_threshold,
                    CampaignParticipant.payment_deadline > now
                )
            )
        )
        entries = entries_result.all()

        if not entries:
            logger.info("No entries need payment reminder")
            return

        logger.info("Sending payment reminders to %d users", len(entries))

        for participant, user, campaign, product in entries:
            title = campaign.title_override or product.title
            selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else 0

            # Check if reminder already sent recently — dedupe by campaign_id
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.campaign_id == campaign.id,
                        Notification.type == "payment_reminder",
                        Notification.status.in_(["pending", "sent"]),
                        Notification.created_at >= now - timedelta(hours=24),
                    )
                )
            )

            if notif_result.scalar_one_or_none():
                continue  # Already attempted reminder recently

            hours_remaining = int((participant.payment_deadline - now).total_seconds() / 3600)

            email_data = {
                "product_title": title,
                "total_price": selling_price * participant.quantity,
                "deadline": participant.payment_deadline.strftime("%d.%m.%Y %H:%M"),
                "hours_remaining": hours_remaining,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{participant.id}"
            }

            html = EmailTemplates.payment_reminder(email_data)

            try:
                send_result = EmailService.send_email(
                    to=user.email,
                    subject=f"⏰ Son {hours_remaining} saat! {title} için ödeme yapın",
                    html=html
                )
            except Exception as exc:
                logger.error("Reminder email exception for %s: %s", user.email, exc)
                send_result = {"status": "error", "error": str(exc)}

            if send_result.get("status") == "skipped":
                notif_status = "skipped"
            elif send_result.get("status") == "error":
                notif_status = "failed"
            else:
                notif_status = "sent"

            notification = Notification(
                user_id=user.id,
                campaign_id=campaign.id,
                type="payment_reminder",
                channel="email",
                subject=f"Payment reminder for {title}",
                status=notif_status,
                sent_at=now if notif_status == "sent" else None,
            )
            db.add(notification)

        await db.commit()
        logger.info("Sent %d payment reminders", len(entries))


@celery_app.task(name="app.tasks.email_tasks.send_payment_success_email")
def send_payment_success_email(participant_id: str):
    """
    Send payment success confirmation email.

    Args:
        participant_id: CampaignParticipant UUID
    """
    import asyncio
    asyncio.run(_send_payment_success_email_async(participant_id))


async def _send_payment_success_email_async(participant_id: str):
    """Async implementation of payment success email."""
    async with AsyncSessionLocal() as db:
        participant_uuid = UUID(participant_id)

        # Get participant with user, campaign, product
        result = await db.execute(
            select(CampaignParticipant, User, Campaign, Product)
            .join(User, CampaignParticipant.user_id == User.id)
            .join(Campaign, CampaignParticipant.campaign_id == Campaign.id)
            .join(Product, Campaign.product_id == Product.id)
            .where(CampaignParticipant.id == participant_uuid)
        )
        row = result.one_or_none()

        if not row:
            logger.error("Participant %s not found", participant_id)
            return

        participant, user, campaign, product = row
        title = campaign.title_override or product.title
        selling_price = float(campaign.selling_price_try_snapshot) if campaign.selling_price_try_snapshot else 0

        email_data = {
            "product_title": title,
            "quantity": participant.quantity,
            "total_price": selling_price * participant.quantity,
            "order_id": str(campaign.id)[:8],
            "lead_time_days": campaign.lead_time_days or 30,
            "estimated_delivery": (datetime.now(timezone.utc) + timedelta(days=campaign.lead_time_days or 30)).strftime("%d.%m.%Y")
        }

        html = EmailTemplates.payment_success(email_data)

        EmailService.send_email(
            to=user.email,
            subject=f"✅ Ödemeniz alındı! {title}",
            html=html
        )

        logger.info("Sent payment success email to %s", user.email)


@celery_app.task(name="app.tasks.email_tasks.send_moq_failed_email")
def send_moq_failed_email(campaign_id: str):
    """
    Send MoQ failed notification.
    Called when not enough payments collected after 48h.

    Args:
        campaign_id: Campaign UUID
    """
    import asyncio
    asyncio.run(_send_moq_failed_email_async(campaign_id))


async def _send_moq_failed_email_async(campaign_id: str):
    """Async implementation of MoQ failed email."""
    async with AsyncSessionLocal() as db:
        campaign_uuid = UUID(campaign_id)

        # Get campaign + product
        result = await db.execute(
            select(Campaign, Product)
            .join(Product, Campaign.product_id == Product.id)
            .where(Campaign.id == campaign_uuid)
        )
        row = result.one_or_none()

        if not row:
            logger.error("Campaign %s not found", campaign_id)
            return

        campaign, product = row
        title = campaign.title_override or product.title

        # Get expired/joined participants
        entries_result = await db.execute(
            select(CampaignParticipant, User)
            .join(User, CampaignParticipant.user_id == User.id)
            .where(
                CampaignParticipant.campaign_id == campaign_uuid,
                CampaignParticipant.status.in_(["expired", "joined"])
            )
        )
        entries = entries_result.all()

        # Count paid
        paid_result = await db.execute(
            select(func.count(CampaignParticipant.id))
            .where(
                CampaignParticipant.campaign_id == campaign_uuid,
                CampaignParticipant.status == "paid"
            )
        )
        paid_count = paid_result.scalar() or 0

        logger.info("Sending MoQ failed emails to %d users", len(entries))

        for participant, user in entries:
            email_data = {
                "product_title": title,
                "moq": campaign.moq or 0,
                "paid_count": paid_count,
                "missing_count": (campaign.moq or 0) - paid_count
            }

            html = EmailTemplates.moq_failed(email_data)

            EmailService.send_email(
                to=user.email,
                subject=f"😔 {title} siparişi iptal edildi",
                html=html
            )

        logger.info("Sent %d MoQ failed emails", len(entries))
