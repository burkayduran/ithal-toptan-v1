"""
Celery Email Tasks
Background jobs for sending emails with retry/backoff and fake-provider support.
"""
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.exc import IntegrityError

from app.tasks.celery_app import celery_app
from app.services.email_service import EmailService
from app.templates.email_templates import EmailTemplates
from app.db.session import AsyncSessionLocal
from app.models.models import (
    User, ProductRequest, WishlistEntry,
    SupplierOffer, Notification,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────

_TRANSIENT_ERRORS = ("error",)  # statuses that justify a retry


def _is_transient(send_result: dict) -> bool:
    """Return True when the send failure warrants a Celery retry."""
    return send_result.get("status") in _TRANSIENT_ERRORS


# ── send_moq_reached_email ────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.email_tasks.send_moq_reached_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute between retries
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def send_moq_reached_email(self, request_id: str, deadline: str):
    """Send MoQ-reached email to all waiting users (called when MoQ is hit)."""
    import asyncio
    asyncio.run(_send_moq_reached_email_async(request_id, deadline))


async def _send_moq_reached_email_async(request_id: str, deadline: str):
    async with AsyncSessionLocal() as db:
        request_uuid = UUID(request_id)

        product_result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == request_uuid)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            logger.error("send_moq_reached_email: product %s not found", request_id)
            return

        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_uuid,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()
        if not offer:
            logger.error("send_moq_reached_email: no selected offer for product %s", request_id)
            return

        entries_result = await db.execute(
            select(WishlistEntry, User)
            .join(User, WishlistEntry.user_id == User.id)
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status == "notified",
            )
        )
        entries = entries_result.all()

        if not entries:
            logger.warning("send_moq_reached_email: no notified entries for %s", request_id)
            return

        logger.info("Sending MoQ-reached emails to %d users for product %s", len(entries), request_id)

        deadline_str = "N/A"
        if deadline:
            try:
                deadline_str = datetime.fromisoformat(deadline).strftime("%d.%m.%Y %H:%M")
            except ValueError:
                pass

        for entry, user in entries:
            email_data = {
                "product_title": product.title,
                "quantity": entry.quantity,
                "unit_price": float(offer.selling_price_try) if offer.selling_price_try else 0,
                "total_price": (float(offer.selling_price_try) * entry.quantity) if offer.selling_price_try else 0,
                "moq": offer.moq,
                "deadline": deadline_str,
                "lead_time_days": offer.lead_time_days or 30,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{entry.id}",
            }

            html = EmailTemplates.moq_reached(email_data)
            send_result = EmailService.send_email(
                to=user.email,
                subject=f"🎉 {product.title} için sipariş hazır! 48 saat içinde ödeme yapın",
                html=html,
            )

            notif_status = "failed" if send_result.get("status") in ("error", "skipped") else "sent"

            # Update existing pending notification (unique constraint: one record per user+request+type)
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.request_id == request_uuid,
                        Notification.type == "moq_reached",
                        Notification.status == "pending",
                    )
                )
            )
            notification = notif_result.scalar_one_or_none()
            if notification:
                notification.status = notif_status

        await db.commit()
        logger.info("MoQ-reached emails done for product %s", request_id)


# ── send_payment_reminders ────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.email_tasks.send_payment_reminders",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def send_payment_reminders(self):
    """
    Send payment-reminder emails.
    Runs every 6 hours via Celery Beat.
    24-hour dedup enforced via uq_notification_user_request_type constraint.
    """
    import asyncio
    asyncio.run(_send_payment_reminders_async())


async def _send_payment_reminders_async():
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)
        reminder_threshold = now + timedelta(hours=24)

        entries_result = await db.execute(
            select(WishlistEntry, User, ProductRequest, SupplierOffer)
            .join(User, WishlistEntry.user_id == User.id)
            .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
            .outerjoin(
                SupplierOffer,
                and_(
                    SupplierOffer.request_id == ProductRequest.id,
                    SupplierOffer.is_selected == True,
                ),
            )
            .where(
                and_(
                    WishlistEntry.status == "notified",
                    WishlistEntry.payment_deadline.isnot(None),
                    WishlistEntry.payment_deadline < reminder_threshold,
                    WishlistEntry.payment_deadline > now,
                )
            )
        )
        entries = entries_result.all()

        if not entries:
            logger.info("send_payment_reminders: no entries need a reminder")
            return

        logger.info("Sending payment reminders to %d users", len(entries))

        for entry, user, product, offer in entries:
            if offer is None:
                logger.warning(
                    "send_payment_reminders: no selected offer for product %s, skipping %s",
                    product.id, user.email,
                )
                continue

            # 24h dedup: check if a notification (any status) already exists
            existing_notif = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.request_id == product.id,
                        Notification.type == "payment_reminder",
                    )
                )
            )
            existing = existing_notif.scalar_one_or_none()
            if existing:
                # Already sent (or attempted) – respect 24h dedup
                continue

            hours_remaining = max(
                0, int((entry.payment_deadline - now).total_seconds() / 3600)
            )

            email_data = {
                "product_title": product.title,
                "total_price": (float(offer.selling_price_try) * entry.quantity) if offer.selling_price_try else 0,
                "deadline": entry.payment_deadline.strftime("%d.%m.%Y %H:%M"),
                "hours_remaining": hours_remaining,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{entry.id}",
            }

            html = EmailTemplates.payment_reminder(email_data)
            send_result = EmailService.send_email(
                to=user.email,
                subject=f"⏰ Son {hours_remaining} saat! {product.title} için ödeme yapın",
                html=html,
            )

            notif_status = "failed" if send_result.get("status") in ("error", "skipped") else "sent"

            notification = Notification(
                user_id=user.id,
                request_id=product.id,
                type="payment_reminder",
                channel="email",
                subject=f"Payment reminder for {product.title}",
                status=notif_status,
            )
            db.add(notification)
            try:
                await db.flush()
            except IntegrityError:
                # Concurrent worker already inserted this notification – skip
                await db.rollback()
                logger.info(
                    "send_payment_reminders: concurrent insert detected for user=%s product=%s, skipping",
                    user.id, product.id,
                )
                continue

        await db.commit()
        logger.info("Payment reminder task complete")


# ── send_payment_success_email ────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.email_tasks.send_payment_success_email",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_payment_success_email(self, entry_id: str):
    """Send payment-success confirmation email."""
    import asyncio
    asyncio.run(_send_payment_success_email_async(entry_id))


async def _send_payment_success_email_async(entry_id: str):
    async with AsyncSessionLocal() as db:
        entry_uuid = UUID(entry_id)

        result = await db.execute(
            select(WishlistEntry, User, ProductRequest, SupplierOffer)
            .join(User, WishlistEntry.user_id == User.id)
            .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
            .join(
                SupplierOffer,
                and_(
                    SupplierOffer.request_id == ProductRequest.id,
                    SupplierOffer.is_selected == True,
                ),
            )
            .where(WishlistEntry.id == entry_uuid)
        )
        row = result.one_or_none()
        if not row:
            logger.error("send_payment_success_email: entry %s not found", entry_id)
            return

        entry, user, product, offer = row

        email_data = {
            "product_title": product.title,
            "quantity": entry.quantity,
            "total_price": (float(offer.selling_price_try) * entry.quantity) if offer.selling_price_try else 0,
            "order_id": str(product.id)[:8],
            "lead_time_days": offer.lead_time_days or 30,
            "estimated_delivery": (
                datetime.now(timezone.utc) + timedelta(days=offer.lead_time_days or 30)
            ).strftime("%d.%m.%Y"),
        }

        html = EmailTemplates.payment_success(email_data)
        EmailService.send_email(
            to=user.email,
            subject=f"✅ Ödemeniz alındı! {product.title}",
            html=html,
        )
        logger.info("Payment success email sent to %s", user.email)


# ── send_moq_failed_email ─────────────────────────────────────────────────────

@celery_app.task(
    name="app.tasks.email_tasks.send_moq_failed_email",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_moq_failed_email(self, request_id: str):
    """Send MoQ-failed notification when payment collection falls short."""
    import asyncio
    asyncio.run(_send_moq_failed_email_async(request_id))


async def _send_moq_failed_email_async(request_id: str):
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func as sql_func

        request_uuid = UUID(request_id)

        product_result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == request_uuid)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            logger.error("send_moq_failed_email: product %s not found", request_id)
            return

        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_uuid,
                SupplierOffer.is_selected == True,
            )
        )
        offer = offer_result.scalar_one_or_none()

        paid_result = await db.execute(
            select(sql_func.count(WishlistEntry.id))
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status == "paid",
            )
        )
        paid_count = paid_result.scalar() or 0

        entries_result = await db.execute(
            select(WishlistEntry, User)
            .join(User, WishlistEntry.user_id == User.id)
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status.in_(["expired", "waiting"]),
            )
        )
        entries = entries_result.all()

        logger.info("Sending MoQ-failed emails to %d users for product %s", len(entries), request_id)

        for entry, user in entries:
            email_data = {
                "product_title": product.title,
                "moq": offer.moq if offer else 0,
                "paid_count": paid_count,
                "missing_count": (offer.moq if offer else 0) - paid_count,
            }
            html = EmailTemplates.moq_failed(email_data)
            EmailService.send_email(
                to=user.email,
                subject=f"😔 {product.title} siparişi iptal edildi",
                html=html,
            )

        logger.info("MoQ-failed emails done for product %s", request_id)
