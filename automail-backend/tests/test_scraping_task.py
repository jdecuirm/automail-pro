"""Tests for the leads.scrape Celery task."""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    """Run a coroutine in a fresh event loop (safe from sync context)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Celery task tests (sync — asyncio.run() cannot nest inside async tests)
# ---------------------------------------------------------------------------


def test_scrape_task_returns_researched_on_success():
    """Task returns status=researched when orchestrator returns a research object."""
    from app.celery_app import celery_app
    from app.tasks.scraping import scrape_lead

    lead_id = str(uuid.uuid4())
    mock_research = MagicMock()
    mock_research.id = uuid.uuid4()

    async def _fake_scrape(lid, session):
        return mock_research

    mock_session = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.services.scraper_orchestrator.scrape_lead", side_effect=_fake_scrape):
        with patch("app.database.get_task_session", _fake_ctx):
            with patch("app.tasks.generation.generate_email"):
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                result = scrape_lead.apply(args=[lead_id])
                celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "researched"
    assert data["research_id"] == str(mock_research.id)
    assert data["lead_id"] == lead_id


def test_scrape_task_returns_failed_when_orchestrator_returns_none():
    """Task returns status=failed when orchestrator returns None (all scrapers failed)."""
    from app.celery_app import celery_app
    from app.tasks.scraping import scrape_lead

    lead_id = str(uuid.uuid4())

    async def _fake_scrape_none(lid, session):
        return None

    mock_session = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.services.scraper_orchestrator.scrape_lead", side_effect=_fake_scrape_none):
        with patch("app.database.get_task_session", _fake_ctx):
            celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
            result = scrape_lead.apply(args=[lead_id])
            celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "failed"
    assert data["research_id"] is None


def test_scrape_task_dispatches_generation_on_success():
    """After successful scrape, leads.generate task is dispatched."""
    from app.celery_app import celery_app
    from app.tasks.scraping import scrape_lead

    lead_id = str(uuid.uuid4())
    mock_research = MagicMock()
    mock_research.id = uuid.uuid4()

    async def _fake_scrape(lid, session):
        return mock_research

    mock_session = AsyncMock()

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.services.scraper_orchestrator.scrape_lead", side_effect=_fake_scrape):
        with patch("app.database.get_task_session", _fake_ctx):
            with patch("app.tasks.generation.generate_email") as mock_generate:
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                result = scrape_lead.apply(args=[lead_id])
                celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    assert result.get()["status"] == "researched"
    mock_generate.delay.assert_called_once_with(lead_id)
