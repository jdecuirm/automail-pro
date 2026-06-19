"""Shared slowapi rate-limiter instance and per-endpoint limit callables."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import get_settings


def _make_limiter() -> Limiter:
    settings = get_settings()
    return Limiter(
        key_func=get_remote_address,
        enabled=settings.rate_limiting_enabled,
    )


limiter = _make_limiter()


def limit_campaigns_create() -> str:
    return get_settings().rate_limit_campaigns_create


def limit_oauth_authorize() -> str:
    return get_settings().rate_limit_oauth_authorize


def limit_emails_approve() -> str:
    return get_settings().rate_limit_emails_approve
