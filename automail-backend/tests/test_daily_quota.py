"""Tests for the daily email send quota service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


async def test_can_send_returns_true_when_no_emails_sent(user_id):
    from app.services.daily_quota import can_send

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 0
    mock_session.execute.return_value = mock_result

    result = await can_send(user_id, mock_session)
    assert result is True


async def test_can_send_returns_false_when_quota_reached(user_id):
    from app.services.daily_quota import can_send

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 50  # at limit
    mock_session.execute.return_value = mock_result

    with patch("app.services.daily_quota.get_settings") as mock_settings:
        mock_settings.return_value.max_emails_per_user_per_day = 50
        result = await can_send(user_id, mock_session)

    assert result is False


async def test_remaining_quota_returns_correct_count(user_id):
    from app.services.daily_quota import remaining_quota

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 12
    mock_session.execute.return_value = mock_result

    with patch("app.services.daily_quota.get_settings") as mock_settings:
        mock_settings.return_value.max_emails_per_user_per_day = 50
        remaining = await remaining_quota(user_id, mock_session)

    assert remaining == 38


async def test_can_send_returns_true_when_under_limit(user_id):
    from app.services.daily_quota import can_send

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 49
    mock_session.execute.return_value = mock_result

    with patch("app.services.daily_quota.get_settings") as mock_settings:
        mock_settings.return_value.max_emails_per_user_per_day = 50
        result = await can_send(user_id, mock_session)

    assert result is True
