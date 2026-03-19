"""
Email Service using Resend API
"""
import logging
from typing import List, Dict, Optional
import resend
from app.core.config import settings

logger = logging.getLogger("ithal_toptan")

# Initialize Resend
if settings.RESEND_API_KEY:
    resend.api_key = settings.RESEND_API_KEY


class EmailService:
    """Handle email sending with Resend."""
    
    @staticmethod
    def send_email(
        to: str,
        subject: str,
        html: str,
        from_email: Optional[str] = None
    ) -> Dict:
        """
        Send an email using Resend.
        
        Args:
            to: Recipient email
            subject: Email subject
            html: HTML body
            from_email: Sender email (defaults to RESEND_FROM_EMAIL)
        
        Returns:
            Response from Resend API
        """
        if settings.EMAIL_PROVIDER == "fake":
            logger.info("Fake email provider: pretending to send email to %s", to)
            return {"status": "sent", "provider": "fake", "id": f"fake-{to}"}

        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not set. Email not sent to %s", to)
            return {"status": "skipped", "reason": "no_api_key"}
        
        try:
            params = {
                "from": from_email or settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            }
            
            response = resend.Emails.send(params)
            logger.info("Email sent to %s: %s", to, response)
            return response
        
        except Exception as e:
            logger.error("Email send failed to %s: %s", to, e)
            return {"status": "error", "error": str(e)}
    
    @staticmethod
    def send_bulk_email(
        recipients: List[str],
        subject: str,
        html: str,
        from_email: Optional[str] = None
    ) -> List[Dict]:
        """
        Send emails to multiple recipients.
        
        Args:
            recipients: List of recipient emails
            subject: Email subject
            html: HTML body
            from_email: Sender email
        
        Returns:
            List of responses
        """
        results = []
        for recipient in recipients:
            result = EmailService.send_email(
                to=recipient,
                subject=subject,
                html=html,
                from_email=from_email
            )
            results.append({"email": recipient, "result": result})
        
        return results
