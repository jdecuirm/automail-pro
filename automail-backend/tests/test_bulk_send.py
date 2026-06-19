"""Tests for POST /api/campaigns/{id}/send-approved bulk send endpoint."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest.fixture
def campaign_id() -> uuid.UUID:
    return uuid.uuid4()


async def test_bulk_send_dispatches_all_within_quota(campaign_id):
    from app.models.email import EmailStatus

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    approved_emails = [MagicMock(id=uuid.uuid4(), status=EmailStatus.approved) for _ in range(3)]

    mock_user = MagicMock()
    mock_user.sender_name = "Test Sender"
    mock_user.sender_company = "Test Co"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign
    mock_result.scalars.return_value.all.return_value = approved_emails
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=mock_user)

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    try:
        with patch(
            "app.services.campaign_service.remaining_quota",
            new_callable=AsyncMock,
            return_value=10,
        ):
            with patch("app.services.campaign_service.send_email_task") as mock_task:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(f"/api/campaigns/{campaign_id}/send-approved")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["dispatched"] == 3
    assert data["blocked_by_quota"] == 0
    assert mock_task.delay.call_count == 3


async def test_bulk_send_respects_quota_limit(campaign_id):
    from app.models.email import EmailStatus

    mock_campaign = MagicMock()
    mock_campaign.id = campaign_id
    mock_campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # 5 approved but quota only allows 2
    approved_emails = [MagicMock(id=uuid.uuid4(), status=EmailStatus.approved) for _ in range(5)]

    mock_user = MagicMock()
    mock_user.sender_name = "Test Sender"
    mock_user.sender_company = "Test Co"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_campaign
    mock_result.scalars.return_value.all.return_value = approved_emails
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=mock_user)

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    try:
        with patch(
            "app.services.campaign_service.remaining_quota",
            new_callable=AsyncMock,
            return_value=2,
        ):
            with patch("app.services.campaign_service.send_email_task") as mock_task:
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as client:
                    resp = await client.post(f"/api/campaigns/{campaign_id}/send-approved")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["dispatched"] == 2
    assert data["blocked_by_quota"] == 3
    assert mock_task.delay.call_count == 2


async def test_bulk_send_campaign_not_found():
    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_execute)

    async def _override_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(f"/api/campaigns/{uuid.uuid4()}/send-approved")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
