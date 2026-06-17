"""HMAC-signed tokens for tracking pixel URLs."""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid


def sign_open_token(lead_id: uuid.UUID, email_id: uuid.UUID, secret: str) -> str:
    """Create a tamper-proof token encoding lead_id and email_id.

    Args:
        lead_id: UUID of the lead.
        email_id: UUID of the email.
        secret: HMAC secret key (TRACKING_SECRET_KEY from config).

    Returns:
        URL-safe base64-encoded token string (no padding).
    """
    payload = f"{lead_id}:{email_id}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()


def verify_open_token(token: str, secret: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Decode and verify a tracking token.

    Args:
        token: Token produced by ``sign_open_token``.
        secret: HMAC secret key to verify against.

    Returns:
        Tuple of (lead_id, email_id).

    Raises:
        ValueError: If the token is malformed, tampered, or uses the wrong secret.
    """
    try:
        padding = "=" * (4 - len(token) % 4) if len(token) % 4 else ""
        raw = base64.urlsafe_b64decode((token + padding).encode()).decode()
        parts = raw.split(":")
        if len(parts) != 3:
            raise ValueError("invalid token format")
        lead_str, email_str, sig = parts
        payload = f"{lead_str}:{email_str}"
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            raise ValueError("invalid token signature")
        return uuid.UUID(lead_str), uuid.UUID(email_str)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"invalid token: {exc}") from exc
