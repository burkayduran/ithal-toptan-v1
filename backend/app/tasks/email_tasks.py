"""
Celery Email Tasks
Background jobs for sending emails
"""
import logging
from typing import List
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, and_
from uuid import UUID

from app.tasks.celery_app import celery_app

logger = logging.getLogger("ithal_toptan")
from app.services.email_service import EmailService
from app.templates.email_templates import EmailTemplates
from app.db.session import AsyncSessionLocal
from app.models.models import (
    User, ProductRequest, WishlistEntry, 
    SupplierOffer, Notification
)
from app.core.config import settings


@celery_app.task(
    name="app.tasks.email_tasks.send_moq_reached_email",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def send_moq_reached_email(request_id: str, deadline: str):
    """
    Send MoQ reached email to all waiting users.
    Called when MoQ threshold is reached.
    
    Args:
        request_id: Product request UUID
        deadline: Payment deadline (ISO format)
    """
    import asyncio
    asyncio.run(_send_moq_reached_email_async(request_id, deadline))


async def _send_moq_reached_email_async(request_id: str, deadline: str):
    """Async implementation of MoQ reached email."""
    async with AsyncSessionLocal() as db:
        request_uuid = UUID(request_id)
        
        # Get product
        product_result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == request_uuid)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            logger.error("Product %s not found", request_id)
            return
        
        # Get offer
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_uuid,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        if not offer:
            logger.error("No offer for product %s", request_id)
            return
        
        # Get notified entries
        entries_result = await db.execute(
            select(WishlistEntry, User)
            .join(User, WishlistEntry.user_id == User.id)
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status == "notified"
            )
        )
        entries = entries_result.all()
        
        if not entries:
            logger.warning("No notified entries for %s", request_id)
            return
        
        logger.info("Sending MoQ reached emails to %d users", len(entries))
        
        # Send emails
        for entry, user in entries:
            email_data = {
                "product_title": product.title,
                "quantity": entry.quantity,
                "unit_price": float(offer.selling_price_try) if offer.selling_price_try else 0,
                "total_price": float(offer.selling_price_try) * entry.quantity if offer.selling_price_try else 0,
                "moq": offer.moq,
                "deadline": datetime.fromisoformat(deadline).strftime("%d.%m.%Y %H:%M"),
                "lead_time_days": offer.lead_time_days or 30,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{entry.id}"
            }
            
            html = EmailTemplates.moq_reached(email_data)

            try:
                send_result = EmailService.send_email(
                    to=user.email,
                    subject=f"🎉 {product.title} için sipariş hazır! 48 saat içinde ödeme yapın",
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
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.request_id == request_uuid,
                        Notification.type == "moq_reached",
                        Notification.status == "pending"
                    )
                )
            )
            notification = notif_result.scalar_one_or_none()

            if notification:
                notification.status = notif_status
        
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
        
        # Get entries that:
        # - status = notified
        # - deadline < 24 hours
        # - not already sent reminder
        entries_result = await db.execute(
            select(WishlistEntry, User, ProductRequest, SupplierOffer)
            .join(User, WishlistEntry.user_id == User.id)
            .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
            # LEFT JOIN so that entries are not silently dropped when a selected offer
            # is missing; those entries are handled gracefully in the loop below.
            .outerjoin(
                SupplierOffer,
                and_(
                    SupplierOffer.request_id == ProductRequest.id,
                    SupplierOffer.is_selected == True
                )
            )
            .where(
                and_(
                    WishlistEntry.status == "notified",
                    WishlistEntry.payment_deadline.isnot(None),
                    WishlistEntry.payment_deadline < reminder_threshold,
                    WishlistEntry.payment_deadline > now
                )
            )
        )
        entries = entries_result.all()

        if not entries:
            logger.info("No entries need payment reminder")
            return

        logger.info("Sending payment reminders to %d users", len(entries))

        for entry, user, product, offer in entries:
            if offer is None:
                logger.warning("No selected offer for product %s, skipping reminder for %s", product.id, user.email)
                continue
            # Check if reminder already sent
            notif_result = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.user_id == user.id,
                        Notification.request_id == product.id,
                        Notification.type == "payment_reminder",
                        Notification.status.in_(["pending", "sent"]),
                        Notification.sent_at >= now - timedelta(hours=24),
                    )
                )
            )

            if notif_result.scalar_one_or_none():
                continue  # Already attempted reminder recently
            
            hours_remaining = int((entry.payment_deadline - now).total_seconds() / 3600)
            
            email_data = {
                "product_title": product.title,
                "total_price": float(offer.selling_price_try) * entry.quantity if offer.selling_price_try else 0,
                "deadline": entry.payment_deadline.strftime("%d.%m.%Y %H:%M"),
                "hours_remaining": hours_remaining,
                "payment_url": f"{settings.FRONTEND_URL}/payment/{entry.id}"
            }
            
            html = EmailTemplates.payment_reminder(email_data)

            try:
                send_result = EmailService.send_email(
                    to=user.email,
                    subject=f"⏰ Son {hours_remaining} saat! {product.title} için ödeme yapın",
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
                request_id=product.id,
                type="payment_reminder",
                channel="email",
                subject=f"Payment reminder for {product.title}",
                status=notif_status,
            )
            db.add(notification)
        
        await db.commit()
        logger.info("Sent %d payment reminders", len(entries))


@celery_app.task(name="app.tasks.email_tasks.send_payment_success_email")
def send_payment_success_email(entry_id: str):
    """
    Send payment success confirmation email.
    
    Args:
        entry_id: WishlistEntry UUID
    """
    import asyncio
    asyncio.run(_send_payment_success_email_async(entry_id))


async def _send_payment_success_email_async(entry_id: str):
    """Async implementation of payment success email."""
    async with AsyncSessionLocal() as db:
        entry_uuid = UUID(entry_id)
        
        # Get entry with user and product
        result = await db.execute(
            select(WishlistEntry, User, ProductRequest, SupplierOffer)
            .join(User, WishlistEntry.user_id == User.id)
            .join(ProductRequest, WishlistEntry.request_id == ProductRequest.id)
            .join(
                SupplierOffer,
                and_(
                    SupplierOffer.request_id == ProductRequest.id,
                    SupplierOffer.is_selected == True
                )
            )
            .where(WishlistEntry.id == entry_uuid)
        )
        row = result.one_or_none()
        
        if not row:
            logger.error("Entry %s not found", entry_id)
            return
        
        entry, user, product, offer = row
        
        email_data = {
            "product_title": product.title,
            "quantity": entry.quantity,
            "total_price": float(offer.selling_price_try) * entry.quantity if offer.selling_price_try else 0,
            "order_id": str(product.id)[:8],
            "lead_time_days": offer.lead_time_days or 30,
            "estimated_delivery": (datetime.now(timezone.utc) + timedelta(days=offer.lead_time_days or 30)).strftime("%d.%m.%Y")
        }
        
        html = EmailTemplates.payment_success(email_data)
        
        EmailService.send_email(
            to=user.email,
            subject=f"✅ Ödemeniz alındı! {product.title}",
            html=html
        )
        
        logger.info("Sent payment success email to %s", user.email)


@celery_app.task(name="app.tasks.email_tasks.send_moq_failed_email")
def send_moq_failed_email(request_id: str):
    """
    Send MoQ failed notification.
    Called when not enough payments collected after 48h.
    
    Args:
        request_id: Product request UUID
    """
    import asyncio
    asyncio.run(_send_moq_failed_email_async(request_id))


async def _send_moq_failed_email_async(request_id: str):
    """Async implementation of MoQ failed email."""
    async with AsyncSessionLocal() as db:
        request_uuid = UUID(request_id)
        
        # Get product
        product_result = await db.execute(
            select(ProductRequest).where(ProductRequest.id == request_uuid)
        )
        product = product_result.scalar_one_or_none()
        
        if not product:
            logger.error("Product %s not found", request_id)
            return
        
        # Get offer
        offer_result = await db.execute(
            select(SupplierOffer).where(
                SupplierOffer.request_id == request_uuid,
                SupplierOffer.is_selected == True
            )
        )
        offer = offer_result.scalar_one_or_none()
        
        # Get expired entries
        entries_result = await db.execute(
            select(WishlistEntry, User)
            .join(User, WishlistEntry.user_id == User.id)
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status.in_(["expired", "waiting"])
            )
        )
        entries = entries_result.all()
        
        # Count paid
        from sqlalchemy import func as sql_func
        paid_result = await db.execute(
            select(sql_func.count(WishlistEntry.id))
            .where(
                WishlistEntry.request_id == request_uuid,
                WishlistEntry.status == "paid"
            )
        )
        paid_count = paid_result.scalar() or 0
        
        logger.info("Sending MoQ failed emails to %d users", len(entries))
        
        for entry, user in entries:
            email_data = {
                "product_title": product.title,
                "moq": offer.moq if offer else 0,
                "paid_count": paid_count,
                "missing_count": (offer.moq if offer else 0) - paid_count
            }
            
            html = EmailTemplates.moq_failed(email_data)
            
            EmailService.send_email(
                to=user.email,
                subject=f"😔 {product.title} siparişi iptal edildi",
                html=html
            )
        
        logger.info("Sent %d MoQ failed emails", len(entries))
