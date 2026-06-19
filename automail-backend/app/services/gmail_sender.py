"""Gmail API sender — builds MIME messages and calls Gmail API."""

from __future__ import annotations

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gmail_credential import GmailCredential
from app.services import google_oauth
from app.services.encryption import decrypt_str, encrypt_str

logger = logging.getLogger(__name__)


class CredentialNotFoundError(Exception):
    """No GmailCredential row found for the given user."""


class GmailSenderError(Exception):
    """Base class for Gmail API errors."""


class CredentialRevokedError(GmailSenderError):
    """Gmail access token revoked — user must reconnect."""


class GmailRateLimitedError(GmailSenderError):
    """Gmail API rate limit hit — Celery task should retry with backoff."""


class EmailValidationError(GmailSenderError):
    """Gmail API rejected the message as malformed."""


def _build_gmail_service(access_token: str) -> Any:
    """Build a Gmail API service object using an access token.

    Args:
        access_token: A valid Google OAuth2 access token.

    Returns:
        A Gmail API Resource object ready to make API calls.
    """
    creds = Credentials(token=access_token)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _build_raw_message(
    from_addr: str,
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    list_unsubscribe: str,
) -> str:
    """Build a base64url-encoded RFC 2822 message for the Gmail API.

    Args:
        from_addr: Sender email address.
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML version of the email body.
        body_text: Plain-text version of the email body.
        list_unsubscribe: RFC 2369 List-Unsubscribe header value.

    Returns:
        Base64url-encoded string of the raw MIME message.
    """
    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = from_addr
    msg["List-Unsubscribe"] = list_unsubscribe
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    return base64.urlsafe_b64encode(msg.as_bytes()).decode()


def _call_gmail_send(service: Any, raw: str) -> str:
    """Synchronous Gmail API call. Returns gmail_message_id.

    Args:
        service: Gmail API Resource object.
        raw: Base64url-encoded raw MIME message string.

    Returns:
        The Gmail message ID assigned to the sent message.
    """
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result["id"]


def _is_token_expired(token_expiry: datetime | None) -> bool:
    """Return True if the token is expired or within 5-minute margin.

    Args:
        token_expiry: Token expiry datetime (aware or naive UTC), or None.

    Returns:
        True if the token should be refreshed before use.
    """
    if token_expiry is None:
        return True
    five_min = timedelta(minutes=5)
    now = datetime.now(timezone.utc)
    # Normalise naive datetimes to UTC
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)
    return now >= token_expiry - five_min


async def send_email(
    user_id: uuid.UUID,
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    session: AsyncSession,
) -> str:
    """Send an email via the user's Gmail account.

    Retrieves the user's stored OAuth credentials, refreshes the access token
    if expired, builds a properly formatted MIME message with CAN-SPAM
    compliance headers, and delivers it via the Gmail API.

    Args:
        user_id: UUID of the app user whose Gmail account to use.
        to: Recipient email address.
        subject: Email subject line.
        body_html: HTML version of the email body.
        body_text: Plain-text fallback of the email body.
        session: Async SQLAlchemy database session.

    Returns:
        The Gmail message ID (string) assigned by Google.

    Raises:
        CredentialNotFoundError: No gmail_credentials row exists for this user.
        CredentialRevokedError: Google returned 401 — user must re-authorize.
        GmailRateLimitedError: Google returned 403 — Celery task should retry.
        EmailValidationError: Google returned 400 or other API error.
    """
    credential: GmailCredential | None = (
        await session.execute(select(GmailCredential).where(GmailCredential.user_id == user_id))
    ).scalar_one_or_none()

    if credential is None:
        raise CredentialNotFoundError(f"No Gmail credential for user {user_id}")

    if _is_token_expired(credential.token_expiry):
        logger.info("gmail_sender: refreshing expired token for user=%s", user_id)
        new_tokens = google_oauth.refresh_access_token(
            credential.encrypted_refresh_token,
            credential.encrypted_access_token,
        )
        credential.encrypted_access_token = encrypt_str(new_tokens["access_token"])
        credential.token_expiry = new_tokens.get("expiry")
        if new_tokens.get("new_refresh_token"):
            credential.encrypted_refresh_token = encrypt_str(new_tokens["new_refresh_token"])
        await session.commit()

    if credential.encrypted_access_token is None:
        raise ValueError("Access token unavailable — user must reconnect Gmail")
    access_token = decrypt_str(credential.encrypted_access_token)
    sender_email = credential.get_email_address()

    list_unsubscribe = f"<mailto:{sender_email}?subject=unsubscribe>"

    raw = _build_raw_message(
        from_addr=sender_email,
        to=to,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        list_unsubscribe=list_unsubscribe,
    )

    service = _build_gmail_service(access_token)

    try:
        gmail_message_id: str = await asyncio.to_thread(_call_gmail_send, service, raw)
    except HttpError as exc:
        status_code = exc.resp.status
        if status_code == 401:
            credential.needs_reconnect = True
            await session.commit()
            raise CredentialRevokedError(
                "Gmail access token revoked — user must reconnect"
            ) from exc
        elif status_code == 403:
            raise GmailRateLimitedError("Gmail rate limit exceeded") from exc
        else:
            raise EmailValidationError(f"Gmail API error {status_code}: {exc}") from exc

    logger.info(
        "gmail_sender: sent email user=%s gmail_id=%s",
        user_id,
        gmail_message_id,
    )
    return gmail_message_id
