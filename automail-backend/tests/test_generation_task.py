"""Tests for the leads.generate Celery task."""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def test_generate_task_returns_drafted_on_success():
    from app.tasks.generation import generate_email

    from app.celery_app import celery_app

    lead_id = str(uuid.uuid4())
    mock_email = MagicMock()
    mock_email.id = uuid.uuid4()

    async def _fake_generate(lid, session):
        return mock_email

    mock_session = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.services.email_generator.generate_email_draft", side_effect=_fake_generate):
        with patch("app.database.get_session_context", _fake_ctx):
            celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
            result = generate_email.apply(args=[lead_id])
            celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "drafted"
    assert data["email_id"] == str(mock_email.id)


def test_generate_task_returns_failed_when_none():
    from app.tasks.generation import generate_email

    from app.celery_app import celery_app

    lead_id = str(uuid.uuid4())

    async def _fake_generate_none(lid, session):
        return None

    mock_session = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch(
        "app.services.email_generator.generate_email_draft", side_effect=_fake_generate_none
    ):
        with patch("app.database.get_session_context", _fake_ctx):
            celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
            result = generate_email.apply(args=[lead_id])
            celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "failed"
    assert data["email_id"] is None
