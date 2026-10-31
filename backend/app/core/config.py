"""Centralized configuration loaded from environment variables."""
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_PATH = (PROJECT_ROOT / "subscription_system.db").as_posix()


class Settings(BaseSettings):
    APP_NAME: str = "Enterprise Subscription & Billing Management System"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Primary PostgreSQL connection URL
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/subscription_db"
    FALLBACK_SQLITE_URL: str = f"sqlite:///{DEFAULT_SQLITE_PATH}"
    AUTO_FALLBACK_TO_SQLITE: bool = True

    # JWT / Security settings
    JWT_SECRET_KEY: str = "enterprise_subscription_system_jwt_secret_key_change_in_production_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 240
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    # Billing worker settings
    BILLING_WORKER_BATCH_SIZE: int = 50
    BILLING_WORKER_MAX_RETRIES: int = 3
    DEFAULT_PAYMENT_TERM_DAYS: int = 14

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
