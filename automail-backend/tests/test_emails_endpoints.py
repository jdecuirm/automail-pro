"""Tests for /api/emails/* endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest.fixture
def email_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def lead_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def mock_email(email_id, lead_id):
    from app.models.email import EmailStatus

    email = MagicMock()
    email.id = email_id
    email.lead_id = lead_id
    email.subject = "Test Subject"
    email.body_html = "<p>Test</p>"
    email.body_text = "Test"
    email.status = EmailStatus.draft
    email.sent_at = None
    email.gmail_message_id = None
    email.error_message = None
    email.created_at = MagicMock()
    email.updated_at = MagicMock()
    email.lead = MagicMock()
    email.lead.name = "Test Lead"
    email.lead.campaign = MagicMock()
    email.lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return email


async def test_get_email_returns_detail(email_id, mock_email):
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/emails/{email_id}")
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(email_id)
    assert data["status"] == "draft"


async def test_approve_email_dispatches_send_task(email_id, mock_email):
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db

    with patch("app.api.emails.send_email_task") as mock_task:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/emails/{email_id}/approve")

    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    mock_task.delay.assert_called_once_with(str(email_id))


async def test_reject_email_changes_status(email_id, mock_email):
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/emails/{email_id}/reject")
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    mock_session.commit.assert_called()


async def test_approve_email_not_found_returns_404():
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(f"/api/emails/{uuid.uuid4()}/approve")
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


async def test_patch_email_updates_subject(email_id, mock_email):
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/emails/{email_id}",
            json={"subject": "Updated Subject"},
        )
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert mock_email.subject == "Updated Subject"


async def test_patch_email_already_approved_returns_409(email_id, mock_email):
    from unittest.mock import AsyncMock

    from app.models.email import EmailStatus

    mock_email.status = EmailStatus.approved

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_session.execute.return_value = mock_execute

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/api/emails/{email_id}",
            json={"subject": "Attempt"},
        )
    app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 409
