"""Tests for Google OAuth service — state signing, URL building, token exchange."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# State signing / verification
# ---------------------------------------------------------------------------


def test_sign_state_returns_base64_string():
    from app.services.google_oauth import sign_state

    state = sign_state("user-123", "my-secret")
    assert isinstance(state, str)
    assert len(state) > 0


def test_verify_state_valid_returns_user_id():
    from app.services.google_oauth import sign_state, verify_state

    user_id = "user-123"
    state = sign_state(user_id, "my-secret")
    returned = verify_state(state, "my-secret")
    assert returned == user_id


def test_verify_state_invalid_signature_raises():
    from app.services.google_oauth import sign_state, verify_state

    state = sign_state("user-123", "correct-secret")
    with pytest.raises(ValueError, match="invalid"):
        verify_state(state, "wrong-secret")


def test_verify_state_expired_raises(monkeypatch):
    from app.services.google_oauth import sign_state, verify_state

    # Create a state with a timestamp 11 minutes in the past
    fake_time = time.time() - 660
    monkeypatch.setattr("app.services.google_oauth.time.time", lambda: fake_time)
    state = sign_state("user-123", "my-secret")

    # Restore real time for verification
    monkeypatch.undo()
    with pytest.raises(ValueError, match="expired"):
        verify_state(state, "my-secret", max_age=600)


def test_verify_state_tampered_payload_raises():
    import base64

    from app.services.google_oauth import verify_state

    bad = base64.urlsafe_b64encode(b"user-123:9999999999:badsig").decode()
    with pytest.raises(ValueError):
        verify_state(bad, "my-secret")


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------


def test_build_auth_url_contains_scopes():
    from app.services.google_oauth import build_auth_url

    url = build_auth_url("signed-state-token")
    assert "gmail.send" in url
    assert "userinfo.email" in url


def test_build_auth_url_contains_state():
    from app.services.google_oauth import build_auth_url

    url = build_auth_url("my-state-value")
    assert "my-state-value" in url


def test_build_auth_url_offline_access():
    from app.services.google_oauth import build_auth_url

    url = build_auth_url("state")
    assert "offline" in url


# ---------------------------------------------------------------------------
# exchange_code_for_tokens (mocked Google)
# ---------------------------------------------------------------------------


def test_exchange_code_for_tokens_returns_expected_keys():
    from app.services.google_oauth import exchange_code_for_tokens

    mock_creds = MagicMock()
    mock_creds.token = "access-token-abc"
    mock_creds.refresh_token = "refresh-token-xyz"
    mock_creds.expiry = None
    mock_creds.id_token = None

    mock_flow = MagicMock()
    mock_flow.credentials = mock_creds

    with patch("app.services.google_oauth._create_flow", return_value=mock_flow):
        with patch(
            "app.services.google_oauth._get_email_from_token",
            return_value="user@gmail.com",
        ):
            result = exchange_code_for_tokens("auth-code-123")

    assert result["access_token"] == "access-token-abc"
    assert result["refresh_token"] == "refresh-token-xyz"
    assert result["email"] == "user@gmail.com"
    assert "expiry" in result


# ---------------------------------------------------------------------------
# refresh_access_token (mocked google.auth)
# ---------------------------------------------------------------------------


def test_refresh_access_token_returns_new_access_token():
    from app.services.encryption import encrypt_str
    from app.services.google_oauth import refresh_access_token

    encrypted_refresh = encrypt_str("old-refresh-token")
    encrypted_access = encrypt_str("old-access-token")

    mock_creds = MagicMock()
    mock_creds.token = "new-access-token"
    # In real google-auth, the refresh token is echoed back unchanged when not
    # rotated (never None), so the inequality check creds.refresh_token != refresh_token
    # correctly returns False and "new_refresh_token" is NOT added to the result.
    mock_creds.refresh_token = "old-refresh-token"  # echoed back, no rotation
    mock_creds.expiry = None

    with patch("app.services.google_oauth.Credentials", return_value=mock_creds):
        with patch("app.services.google_oauth.Request"):
            result = refresh_access_token(encrypted_refresh, encrypted_access)

    assert result["access_token"] == "new-access-token"


def test_refresh_access_token_handles_rotation():
    """If Google returns a new refresh_token, it must be included in the result."""
    from app.services.encryption import encrypt_str
    from app.services.google_oauth import refresh_access_token

    encrypted_refresh = encrypt_str("old-refresh")
    mock_creds = MagicMock()
    mock_creds.token = "new-access"
    mock_creds.refresh_token = "rotated-refresh"
    mock_creds.expiry = None

    with patch("app.services.google_oauth.Credentials", return_value=mock_creds):
        with patch("app.services.google_oauth.Request"):
            result = refresh_access_token(encrypted_refresh, None)

    assert result["new_refresh_token"] == "rotated-refresh"
