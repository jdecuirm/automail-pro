"""Tests for Gmail sender service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def mock_credential(user_id):
    from app.services.encryption import encrypt_str

    cred = MagicMock()
    cred.user_id = user_id
    cred.encrypted_refresh_token = encrypt_str("fake-refresh")
    cred.encrypted_access_token = encrypt_str("fake-access")
    cred.token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    cred.needs_reconnect = False
    cred.get_email_address.return_value = "sender@gmail.com"
    return cred


async def test_send_email_success(user_id, mock_credential):
    from app.services.gmail_sender import send_email

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_credential
    mock_session.execute.return_value = mock_execute

    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {"id": "msg-id-123"}

    with patch("app.services.gmail_sender._build_gmail_service", return_value=mock_service):
        gmail_id = await send_email(
            user_id=user_id,
            to="lead@example.com",
            subject="Hello!",
            body_html="<p>Hi</p>",
            body_text="Hi",
            session=mock_session,
        )

    assert gmail_id == "msg-id-123"


async def test_send_email_includes_list_unsubscribe_header(user_id, mock_credential):
    """The raw MIME message must include List-Unsubscribe and List-Unsubscribe-Post."""
    from app.services.gmail_sender import _build_raw_message

    raw = _build_raw_message(
        from_addr="sender@gmail.com",
        to="lead@example.com",
        subject="Test",
        body_html="<p>Test</p>",
        body_text="Test",
        list_unsubscribe="<mailto:sender@gmail.com?subject=unsubscribe>",
    )
    import base64

    decoded = base64.urlsafe_b64decode(raw.encode()).decode(errors="replace")
    assert "List-Unsubscribe" in decoded
    assert "List-Unsubscribe-Post" in decoded


async def test_send_email_credential_not_found_raises(user_id):
    from app.services.gmail_sender import CredentialNotFound, send_email

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute

    with pytest.raises(CredentialNotFound):
        await send_email(
            user_id=user_id,
            to="lead@example.com",
            subject="Hi",
            body_html="<p>Hi</p>",
            body_text="Hi",
            session=mock_session,
        )


async def test_send_email_401_raises_credential_revoked(user_id, mock_credential):
    from googleapiclient.errors import HttpError

    from app.services.gmail_sender import CredentialRevoked, send_email

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_credential
    mock_session.execute.return_value = mock_execute

    http_error = HttpError(resp=MagicMock(status=401), content=b"Unauthorized")

    mock_service = MagicMock()
    mock_service.users().messages().send().execute.side_effect = http_error

    with patch("app.services.gmail_sender._build_gmail_service", return_value=mock_service):
        with pytest.raises(CredentialRevoked):
            await send_email(
                user_id=user_id,
                to="lead@example.com",
                subject="Hi",
                body_html="<p>Hi</p>",
                body_text="Hi",
                session=mock_session,
            )

    # Credential must be marked needs_reconnect=True
    assert mock_credential.needs_reconnect is True


async def test_send_email_403_raises_gmail_rate_limited(user_id, mock_credential):
    from googleapiclient.errors import HttpError

    from app.services.gmail_sender import GmailRateLimited, send_email

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_credential
    mock_session.execute.return_value = mock_execute

    http_error = HttpError(resp=MagicMock(status=403), content=b"Rate limit exceeded")

    mock_service = MagicMock()
    mock_service.users().messages().send().execute.side_effect = http_error

    with patch("app.services.gmail_sender._build_gmail_service", return_value=mock_service):
        with pytest.raises(GmailRateLimited):
            await send_email(
                user_id=user_id,
                to="lead@example.com",
                subject="Hi",
                body_html="<p>Hi</p>",
                body_text="Hi",
                session=mock_session,
            )


async def test_token_refresh_when_expired(user_id, mock_credential):
    """When token is expired, gmail_sender must refresh before calling API."""
    from app.services.gmail_sender import send_email

    mock_credential.token_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)

    # Capture the encrypted bytes *before* send_email overwrites them post-refresh.
    expected_refresh_token = mock_credential.encrypted_refresh_token
    expected_access_token = mock_credential.encrypted_access_token

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_credential
    mock_session.execute.return_value = mock_execute

    mock_service = MagicMock()
    mock_service.users().messages().send().execute.return_value = {"id": "msg-refreshed"}

    new_token_data = {
        "access_token": "new-access",
        "expiry": datetime.now(timezone.utc) + timedelta(hours=1),
    }

    with patch("app.services.gmail_sender._build_gmail_service", return_value=mock_service):
        with patch(
            "app.services.gmail_sender.google_oauth.refresh_access_token",
            return_value=new_token_data,
        ) as mock_refresh:
            gmail_id = await send_email(
                user_id=user_id,
                to="lead@example.com",
                subject="Hi",
                body_html="<p>Hi</p>",
                body_text="Hi",
                session=mock_session,
            )

    mock_refresh.assert_called_once_with(
        expected_refresh_token,
        expected_access_token,
    )
    assert gmail_id == "msg-refreshed"
