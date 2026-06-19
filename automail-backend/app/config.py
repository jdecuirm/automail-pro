from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET_KEY = "dev-secret-change-me"
_DEV_TRACKING_KEY = "dev-tracking-key-change-me"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/automail"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Anthropic
    anthropic_api_key: SecretStr | None = None
    claude_model: Literal["claude-haiku-4-5"] = "claude-haiku-4-5"
    claude_max_tokens: int = 1024

    # Google OAuth (Gmail)
    google_client_id: str = ""
    google_client_secret: SecretStr | None = None
    google_redirect_uri: str = "http://localhost:8000/api/oauth/google/callback"

    # Fernet encryption key — generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    fernet_key: SecretStr  # Required — no default, must be set in .env

    # App — defaults are dev-only; validator raises if used outside localhost
    app_secret_key: SecretStr = SecretStr(_DEV_SECRET_KEY)
    tracking_secret_key: SecretStr = SecretStr(_DEV_TRACKING_KEY)
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"

    # Scraping
    scrape_rate_limit_seconds: int = 2
    scrape_cache_ttl_days: int = 7
    scrape_user_agent: str = "AutoMailPro/1.0 (+https://github.com/jdecuirm/automail-pro)"
    scrape_static_timeout: int = 15
    scrape_dynamic_timeout: int = 30
    scrape_max_retries: int = 3
    scrape_robots_cache_ttl_seconds: int = 86400  # 24h

    # Email
    max_emails_per_user_per_day: int = 50

    # CORS — stored as comma-separated string; pydantic-settings parses list[str] as JSON
    # so we keep it as str and expose a property to split at usage time
    cors_allow_origins: str = "http://localhost:5173"

    # Demo auth — temporary until Stage J introduces real user management
    demo_user_id: str = "00000000-0000-0000-0000-000000000001"

    # CSV upload limits
    csv_max_size_mb: int = 5
    csv_max_rows: int = 10_000

    @model_validator(mode="after")
    def _reject_dev_secrets_in_production(self) -> "Settings":
        is_prod = "localhost" not in self.app_base_url and "127.0.0.1" not in self.app_base_url
        if is_prod:
            if self.app_secret_key.get_secret_value() == _DEV_SECRET_KEY:
                raise ValueError(
                    "APP_SECRET_KEY must be set to a strong random value in production"
                )
            if self.tracking_secret_key.get_secret_value() == _DEV_TRACKING_KEY:
                raise ValueError(
                    "TRACKING_SECRET_KEY must be set to a strong random value in production"
                )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
