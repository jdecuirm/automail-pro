from functools import lru_cache
from typing import Any, Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/oauth/google/callback"

    # App
    app_secret_key: SecretStr = SecretStr("dev-secret-change-me")
    tracking_secret_key: SecretStr = SecretStr("dev-tracking-key-change-me")
    app_base_url: str = "http://localhost:8000"
    frontend_base_url: str = "http://localhost:5173"

    # Scraping
    scrape_rate_limit_seconds: int = 2
    scrape_cache_ttl_days: int = 7
    scrape_user_agent: str = (
        "AutoMailPro/1.0 (+https://github.com/jdecuirm/automail-pro)"
    )

    # Email
    max_emails_per_user_per_day: int = 50

    # CORS
    cors_allow_origins: list[str] = ["http://localhost:5173"]

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> Any:
        """Parse CORS origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
