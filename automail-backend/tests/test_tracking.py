"""Tests for the tracking pixel endpoint (Stage H)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.utils.url_signer import sign_open_token

SETTINGS = get_settings()
SECRET = SETTINGS.tracking_secret_key.get_secret_value()

TRANSPARENT_PNG_HEADER = b"\x89PNG"


@pytest.fixture
def lead_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def email_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def valid_token(lead_id: uuid.UUID, email_id: uuid.UUID) -> str:
    return sign_open_token(lead_id, email_id, SECRET)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_session(existing_event=None) -> AsyncMock:
    """Return a mock AsyncSession with configurable scalar_one_or_none result."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_event
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    return mock_session


def _override_db(mock_session: AsyncSession):
    """Return a FastAPI dependency override for get_db."""

    async def _inner() -> AsyncGenerator[AsyncSession, None]:
        yield mock_session

    return _inner


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_token_returns_png(
    lead_id: uuid.UUID, email_id: uuid.UUID, valid_token: str
) -> None:
    """Valid token returns 200 with PNG content."""
    mock_session = _make_mock_session(existing_event=None)

    mock_lead = MagicMock()
    mock_lead.status = "sent"
    mock_email = MagicMock()

    # Sequence of execute() calls:
    # 1st: load lead  → scalar_one_or_none returns mock_lead
    # 2nd: load email → scalar_one_or_none returns mock_email
    # 3rd: dedup check → scalar_one_or_none returns None
    mock_result_lead = MagicMock()
    mock_result_lead.scalar_one_or_none.return_value = mock_lead
    mock_result_email = MagicMock()
    mock_result_email.scalar_one_or_none.return_value = mock_email
    mock_result_dedup = MagicMock()
    mock_result_dedup.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(
        side_effect=[mock_result_lead, mock_result_email, mock_result_dedup]
    )

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/track/open/{valid_token}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:4] == TRANSPARENT_PNG_HEADER


@pytest.mark.asyncio
async def test_invalid_token_still_returns_png() -> None:
    """Invalid/tampered token returns 200 PNG (no broken image in email)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/track/open/invalid-garbage-token")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:4] == TRANSPARENT_PNG_HEADER


@pytest.mark.asyncio
async def test_dedup_does_not_record_second_open(
    lead_id: uuid.UUID, email_id: uuid.UUID, valid_token: str
) -> None:
    """If a TrackingEvent already exists, no new event is recorded."""
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    existing_event = MagicMock()  # simulate an existing TrackingEvent
    mock_lead = MagicMock()
    mock_lead.status = "sent"
    mock_email = MagicMock()

    mock_result_lead = MagicMock()
    mock_result_lead.scalar_one_or_none.return_value = mock_lead
    mock_result_email = MagicMock()
    mock_result_email.scalar_one_or_none.return_value = mock_email
    mock_result_dedup = MagicMock()
    mock_result_dedup.scalar_one_or_none.return_value = existing_event  # already exists

    mock_session.execute = AsyncMock(
        side_effect=[mock_result_lead, mock_result_email, mock_result_dedup]
    )

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/track/open/{valid_token}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.content[:4] == TRANSPARENT_PNG_HEADER
    # add() must NOT have been called — no new event
    mock_session.add.assert_not_called()
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_missing_lead_returns_png(
    lead_id: uuid.UUID, email_id: uuid.UUID, valid_token: str
) -> None:
    """Valid token but lead not in DB still returns 200 PNG."""
    mock_session = AsyncMock(spec=AsyncSession)

    mock_result_lead = MagicMock()
    mock_result_lead.scalar_one_or_none.return_value = None  # lead missing
    mock_result_email = MagicMock()
    mock_result_email.scalar_one_or_none.return_value = None

    mock_session.execute = AsyncMock(side_effect=[mock_result_lead, mock_result_email])

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/track/open/{valid_token}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.content[:4] == TRANSPARENT_PNG_HEADER


@pytest.mark.asyncio
async def test_lead_status_not_advanced_if_already_opened(
    lead_id: uuid.UUID, email_id: uuid.UUID, valid_token: str
) -> None:
    """Lead already at 'opened' status: record event but don't regress status."""
    from app.models.lead import LeadStatus

    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    mock_lead = MagicMock()
    mock_lead.status = LeadStatus.opened  # already opened
    mock_email = MagicMock()

    mock_result_lead = MagicMock()
    mock_result_lead.scalar_one_or_none.return_value = mock_lead
    mock_result_email = MagicMock()
    mock_result_email.scalar_one_or_none.return_value = mock_email
    mock_result_dedup = MagicMock()
    mock_result_dedup.scalar_one_or_none.return_value = None  # first open

    mock_session.execute = AsyncMock(
        side_effect=[mock_result_lead, mock_result_email, mock_result_dedup]
    )

    app.dependency_overrides[get_db] = _override_db(mock_session)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/track/open/{valid_token}")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    # Status must remain opened (not changed by the handler)
    assert mock_lead.status == LeadStatus.opened
    # Event must still be recorded even when status is already opened
    mock_session.add.assert_called_once()
