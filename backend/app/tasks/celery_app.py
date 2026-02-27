"""
Celery configuration for background tasks
"""
import asyncio
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings


def run_async(coro):
    """Execute *coro* in a fresh event loop, closing the loop when done.

    Using a fresh loop per Celery task is safe in prefork workers because
    each worker process has its own Python interpreter with no running loop.
    The explicit create/close pattern avoids resource leaks that can occur
    when asyncio.run() is used inside nested coroutines or test harnesses.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# Create Celery app
celery_app = Celery(
    "toplu_alisveris",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.moq_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Istanbul",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    result_expires=3600,  # 1 hour
)

# Periodic tasks (Celery Beat)
celery_app.conf.beat_schedule = {
    # Her 30 dakikada bir expired entry'leri kontrol et
    "cleanup-expired-entries": {
        "task": "app.tasks.moq_tasks.cleanup_all_expired",
        "schedule": crontab(minute="*/30"),
    },
    # Her 6 saatte bir payment reminder gönder
    "send-payment-reminders": {
        "task": "app.tasks.email_tasks.send_payment_reminders",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}
