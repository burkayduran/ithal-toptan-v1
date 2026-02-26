from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "İthal Toptan 2.0"
    DEBUG: bool = True
    APP_VERSION: str = "2.0.0"

    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    # JWT signing algorithm – declared here so that ALGORITHM=HS256 in .env
    # is accepted rather than rejected as an unknown extra field.
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # iyzico (optional for now)
    IYZICO_API_KEY: Optional[str] = None
    IYZICO_SECRET_KEY: Optional[str] = None
    IYZICO_BASE_URL: str = "https://sandbox-api.iyzipay.com"

    # Email (optional for now)
    EMAIL_PROVIDER: str = "resend"  # resend | fake
    RESEND_API_KEY: Optional[str] = None
    RESEND_FROM_EMAIL: Optional[str] = None

    # TCMB
    TCMB_API_URL: str = "https://evds2.tcmb.gov.tr"

    # MoQ sync strategy: "strict" (sync after every write) | "lazy" (sync only on miss/mismatch)
    MOQ_SYNC_STRATEGY: str = "lazy"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",   # tolerate any extra keys present in .env / environment
    )


settings = Settings()
