"""Quick smoke test for fake email provider."""
import os

os.environ["EMAIL_PROVIDER"] = "fake"
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./dummy.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.services.email_service import EmailService  # noqa: E402


if __name__ == "__main__":
    result = EmailService.send_email(
        to="test@example.com",
        subject="Fake Provider Test",
        html="<p>Hello</p>",
    )
    assert result.get("status") == "sent", result
    assert result.get("provider") == "fake", result
    print("OK", result)
