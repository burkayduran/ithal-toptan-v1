from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "İthal Toptan 2.0"
    DEBUG: bool = False
    APP_VERSION: str = "2.0.0"
    
    # Security
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days
    
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
    # Fallback USD/TRY rate used when live rate cannot be fetched.
    # Set via env var USD_TRY_FALLBACK_RATE. Update regularly in production.
    USD_TRY_FALLBACK_RATE: float = 50.0
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
