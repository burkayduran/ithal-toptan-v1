from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Toplu Alışveriş Platformu"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Frontend / CORS
    FRONTEND_URL: str = "http://localhost:3000"
    # Comma-separated extra allowed origins (optional)
    EXTRA_CORS_ORIGINS: str = ""

    # iyzico (optional)
    IYZICO_API_KEY: Optional[str] = None
    IYZICO_SECRET_KEY: Optional[str] = None
    IYZICO_BASE_URL: str = "https://sandbox-api.iyzipay.com"

    # Email
    # EMAIL_PROVIDER: "resend" | "fake"
    #   "fake"  – always succeeds without hitting any external API (test mode)
    #   "resend" – uses RESEND_API_KEY (falls back to skipped if key missing)
    EMAIL_PROVIDER: str = "resend"
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = None

    # TCMB
    TCMB_API_URL: str = "https://evds2.tcmb.gov.tr"

    # Sentry (optional)
    SENTRY_DSN: Optional[str] = None

    # Rate limiting (requests per minute)
    RATE_LIMIT_AUTH: str = "10/minute"
    RATE_LIMIT_WISHLIST_ADD: str = "30/minute"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
