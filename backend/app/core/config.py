"""Application configuration — loaded from environment variables."""
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://cardnet:cardnet@localhost:5432/cardnet"

    # ── Auth ──────────────────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_32_BYTE_RANDOM_STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS / Security ───────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    TRUSTED_HOSTS: Optional[List[str]] = None

    # ── File Uploads ──────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 50
    UPLOAD_DIR: str = "uploads"

    # ── ML ────────────────────────────────────────────────────────────────────
    MODEL_DIR: str = "ml_models"
    ACTIVE_MODEL_VERSION: Optional[str] = None

    # ── Fraud Thresholds (configurable, unvalidated defaults) ─────────────────
    FRAUD_THRESHOLD_LOW: float = 0.3    # Below = low risk
    FRAUD_THRESHOLD_HIGH: float = 0.7   # Above = high risk

    # ── App ───────────────────────────────────────────────────────────────────
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"


settings = Settings()
