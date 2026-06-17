"""Google OAuth 2.0 flow management for Gmail authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import get_settings
from app.services.encryption import decrypt_str

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _create_flow() -> Flow:
    settings = get_settings()
    if not settings.google_client_secret:
        raise ValueError(
            "GOOGLE_CLIENT_SECRET is not configured — set it in .env to use Gmail OAuth"
        )
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret.get_secret_value(),
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def _get_email_from_token(id_token_str: str | None, access_token: str) -> str:
    """Fetch user email from Google userinfo endpoint using the access token."""
    import httpx

    resp = httpx.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["email"]


def sign_state(user_id: str, secret: str) -> str:
    """Create a signed, time-stamped state string for CSRF protection.

    Format (base64url-encoded): ``{user_id}:{timestamp}:{hmac_hex}``
    """
    ts = str(int(time.time()))
    payload = f"{user_id}:{ts}"
    h = hmac.new(key=secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
    sig = h.hexdigest()
    token = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(token.encode()).decode()


def verify_state(state: str, secret: str, max_age: int = 600) -> str:
    """Verify a signed state string. Returns user_id on success.

    Args:
        state: Base64url-encoded state token produced by ``sign_state``.
        secret: The HMAC secret used to sign the state.
        max_age: Maximum allowed age of the state in seconds (default 600).

    Returns:
        The user_id embedded in the state.

    Raises:
        ValueError: If signature is invalid or state is expired.
    """
    try:
        decoded = base64.urlsafe_b64decode(state.encode()).decode()
        parts = decoded.split(":")
        if len(parts) != 3:
            raise ValueError("malformed state — expected 3 colon-separated parts")
        user_id, ts_str, sig = parts
        payload = f"{user_id}:{ts_str}"
        h = hmac.new(key=secret.encode(), msg=payload.encode(), digestmod=hashlib.sha256)
        expected_sig = h.hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("invalid signature")
        if time.time() - int(ts_str) > max_age:
            raise ValueError("state expired")
        return user_id
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"invalid state: {exc}") from exc


def build_auth_url(state: str) -> str:
    """Build the Google OAuth consent URL with the signed state parameter.

    Args:
        state: Signed state token to embed in the URL for CSRF protection.

    Returns:
        The full authorization URL to redirect the user to.
    """
    flow = _create_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
    )
    return auth_url


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange an authorization code for access + refresh tokens and user email.

    Args:
        code: The authorization code returned by Google after user consent.

    Returns:
        Dict with keys: access_token, refresh_token, expiry (datetime | None), email.
    """
    flow = _create_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials

    email = _get_email_from_token(creds.id_token, creds.token)

    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry,
        "email": email,
    }


def refresh_access_token(
    encrypted_refresh: bytes,
    encrypted_access: bytes | None,
) -> dict[str, Any]:
    """Refresh an expired access token using the stored refresh token.

    Args:
        encrypted_refresh: Fernet-encrypted refresh token bytes.
        encrypted_access: Fernet-encrypted access token bytes, or None.

    Returns:
        Dict with keys: access_token, expiry (datetime | None),
        and optionally new_refresh_token if Google rotated it.
    """
    settings = get_settings()
    refresh_token = decrypt_str(encrypted_refresh)
    access_token = decrypt_str(encrypted_access) if encrypted_access else None

    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret.get_secret_value()
        if settings.google_client_secret
        else "",
    )
    creds.refresh(Request())

    result: dict[str, Any] = {
        "access_token": creds.token,
        "expiry": creds.expiry,
    }
    if creds.refresh_token and creds.refresh_token != refresh_token:
        result["new_refresh_token"] = creds.refresh_token

    return result
