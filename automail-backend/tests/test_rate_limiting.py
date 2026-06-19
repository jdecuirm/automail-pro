"""Rate limiting integration and configuration tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

MINIMAL_CSV = b"name,email,company\nAlice,alice@example.com,ACME Corp"


async def test_rate_limiting_disabled_allows_repeated_requests(
    campaign_client: AsyncClient,
) -> None:
    """With RATE_LIMITING_ENABLED=false, 15 rapid POSTs all succeed — no 429.

    In CI, backend-ci.yml sets RATE_LIMITING_ENABLED=false so the module-level
    limiter is instantiated with enabled=False.  This test skips when the
    environment has rate limiting turned on (local dev default).
    """
    from app.limiter import limiter

    if limiter.enabled:
        pytest.skip(
            "Rate limiting is enabled in this environment. "
            "Set RATE_LIMITING_ENABLED=false to run this test."
        )

    results: list[int] = []
    for i in range(15):
        response = await campaign_client.post(
            "/api/campaigns",
            data={"name": f"RL Bypass Test {i}"},
            files={"file": ("leads.csv", MINIMAL_CSV, "text/csv")},
        )
        results.append(response.status_code)

    assert 429 not in results, f"Got unexpected 429 with rate limiting disabled: {results}"


async def test_limiter_disabled_when_setting_is_false() -> None:
    """A Limiter created with rate_limiting_enabled=False has _enabled=False."""
    from cryptography.fernet import Fernet
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    from app.config import Settings

    settings = Settings(
        _env_file=None,
        fernet_key=Fernet.generate_key().decode(),
        rate_limiting_enabled=False,
    )
    test_limiter = Limiter(
        key_func=get_remote_address,
        enabled=settings.rate_limiting_enabled,
    )
    assert test_limiter.enabled is False


async def test_rate_limit_callables_read_from_settings() -> None:
    """Callable limits return values from Settings, not hardcoded strings.

    Verifies FIX 3: rate limits are configurable via environment variables
    rather than being burned into the decorator strings.
    """
    from unittest.mock import patch

    from cryptography.fernet import Fernet

    from app.config import Settings
    from app.limiter import limit_campaigns_create, limit_emails_approve, limit_oauth_authorize

    custom = Settings(
        _env_file=None,
        fernet_key=Fernet.generate_key().decode(),
        rate_limit_campaigns_create="3/hour",
        rate_limit_oauth_authorize="2/hour",
        rate_limit_emails_approve="50/hour",
    )

    with patch("app.limiter.get_settings", return_value=custom):
        assert limit_campaigns_create() == "3/hour"
        assert limit_oauth_authorize() == "2/hour"
        assert limit_emails_approve() == "50/hour"
