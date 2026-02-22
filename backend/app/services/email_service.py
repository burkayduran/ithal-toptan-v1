"""
Email Service

Supports two providers controlled by the EMAIL_PROVIDER env variable:
  - "resend"  (default) – sends via Resend API; requires RESEND_API_KEY.
  - "fake"              – no network call; always returns a controlled
                          success response (useful for tests / CI).
"""
import logging
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Handle email sending with pluggable providers."""

    @staticmethod
    def send_email(
        to: str,
        subject: str,
        html: str,
        from_email: Optional[str] = None,
    ) -> Dict:
        """
        Send a single email.

        Returns a dict that always contains a ``status`` key:
          - "fake"    – EMAIL_PROVIDER=fake; no real send
          - "sent"    – successfully delivered to provider
          - "skipped" – no API key configured
          - "error"   – provider returned an error
        """
        provider = settings.EMAIL_PROVIDER.lower()

        # ── Fake provider (test / CI mode) ────────────────────────────────────
        if provider == "fake":
            logger.info("FAKE EMAIL to=%s subject=%s", to, subject)
            return {"status": "fake", "to": to, "subject": subject}

        # ── Resend provider ───────────────────────────────────────────────────
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set – email to %s skipped", to)
            return {"status": "skipped", "reason": "no_api_key"}

        try:
            import resend  # noqa: PLC0415
            resend.api_key = settings.RESEND_API_KEY
            params = {
                "from": from_email or settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            response = resend.Emails.send(params)
            logger.info("Email sent to %s: %s", to, response)
            return response
        except Exception as exc:
            logger.error("Email send failed to %s: %s", to, exc)
            return {"status": "error", "error": str(exc)}

    @staticmethod
    def send_bulk_email(
        recipients: List[str],
        subject: str,
        html: str,
        from_email: Optional[str] = None,
    ) -> List[Dict]:
        """Send the same email to multiple recipients."""
        return [
            {"email": r, "result": EmailService.send_email(r, subject, html, from_email)}
            for r in recipients
        ]
