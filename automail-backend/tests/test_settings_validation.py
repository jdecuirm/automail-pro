"""Tests for settings validation and startup requirements."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_fernet_key_field_is_required() -> None:
    """Settings.fernet_key has no default — missing it raises ValidationError at init."""
    from app.config import Settings

    with pytest.raises(ValidationError, match="fernet_key"):
        Settings(
            _env_file=None,
            fernet_key=None,  # type: ignore[arg-type]
        )


def test_fernet_key_accepts_valid_key() -> None:
    """A properly generated Fernet key is accepted without error."""
    from cryptography.fernet import Fernet

    from app.config import Settings

    key = Fernet.generate_key().decode()
    settings = Settings(_env_file=None, fernet_key=key)
    assert settings.fernet_key.get_secret_value() == key


def test_dev_secrets_rejected_in_production() -> None:
    """Dev-default secrets are rejected when APP_BASE_URL points to a real domain.

    We pass app_secret_key explicitly so the test does not depend on the CI
    environment having (or not having) APP_SECRET_KEY in os.environ.
    """
    from cryptography.fernet import Fernet

    from app.config import _DEV_SECRET_KEY, Settings

    with pytest.raises(ValueError, match="APP_SECRET_KEY"):
        Settings(
            _env_file=None,
            fernet_key=Fernet.generate_key().decode(),
            app_base_url="https://automail.example.com",
            app_secret_key=_DEV_SECRET_KEY,  # force dev default regardless of env
        )


def test_rate_limiting_enabled_defaults_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rate limiting is on by default.

    monkeypatch removes RATE_LIMITING_ENABLED from os.environ so Settings
    falls back to the field default (True) instead of the CI value (false).
    """
    from cryptography.fernet import Fernet

    from app.config import Settings

    monkeypatch.delenv("RATE_LIMITING_ENABLED", raising=False)
    settings = Settings(_env_file=None, fernet_key=Fernet.generate_key().decode())
    assert settings.rate_limiting_enabled is True


def test_rate_limiting_can_be_disabled() -> None:
    """RATE_LIMITING_ENABLED=false disables the limiter (used in CI).

    Constructor kwargs take priority over os.environ in pydantic-settings,
    so this test is CI-agnostic.
    """
    from cryptography.fernet import Fernet

    from app.config import Settings

    settings = Settings(
        _env_file=None,
        fernet_key=Fernet.generate_key().decode(),
        rate_limiting_enabled=False,
    )
    assert settings.rate_limiting_enabled is False
