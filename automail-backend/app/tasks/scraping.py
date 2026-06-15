"""Celery task: scrape a single lead."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import httpx

from app.celery_app import celery_app
from app.services.scraper_exceptions import ScraperTimeoutError

logger = logging.getLogger(__name__)


@celery_app.task(
    name="leads.scrape",
    bind=True,
    max_retries=3,
    autoretry_for=(ScraperTimeoutError, httpx.NetworkError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def scrape_lead(self: Any, lead_id: str) -> dict[str, Any]:
    """Scrape a lead's website and persist a LeadResearch row."""
    from app.database import get_task_session as get_session_context
    from app.services import scraper_orchestrator
    from app.tasks.generation import generate_email

    lead_uuid = uuid.UUID(lead_id)

    async def _run() -> dict[str, Any]:
        async with get_session_context() as session:
            research = await scraper_orchestrator.scrape_lead(lead_uuid, session)
            return {
                "lead_id": lead_id,
                "status": "researched" if research else "failed",
                "research_id": str(research.id) if research else None,
            }

    try:
        result = asyncio.run(_run())
        # Dispatch generation AFTER scraping completes (post-commit pattern)
        if result["status"] == "researched":
            generate_email.delay(lead_id)
        return result
    except (ScraperTimeoutError, httpx.NetworkError):
        raise  # autoretry_for handles these
    except Exception as exc:
        logger.exception("scrape_lead task failed for lead=%s: %s", lead_id, exc)
        raise
