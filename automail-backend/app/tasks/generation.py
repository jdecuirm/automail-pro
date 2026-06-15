"""Celery task: generate email draft for a single lead via Claude."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

import anthropic
import httpx

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="leads.generate",
    bind=True,
    max_retries=2,
    autoretry_for=(httpx.TimeoutException, anthropic.APIConnectionError),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
)
def generate_email(self: Any, lead_id: str) -> dict[str, Any]:
    """Generate a personalized email draft via Claude and persist it.

    Returns:
        dict with keys: lead_id (str), status ("drafted" | "failed"), email_id (str | None)
    """
    from app.database import get_task_session as get_session_context
    from app.services import email_generator

    try:
        lead_uuid = uuid.UUID(lead_id)

        async def _run() -> dict[str, Any]:
            async with get_session_context() as session:
                email = await email_generator.generate_email_draft(lead_uuid, session)
                if email is None:
                    logger.warning("generate_email: lead=%s returned no draft", lead_id)
                return {
                    "lead_id": lead_id,
                    "status": "drafted" if email else "failed",
                    "email_id": str(email.id) if email else None,
                }

        return asyncio.run(_run())
    except (httpx.TimeoutException, anthropic.APIConnectionError):
        raise  # autoretry_for handles these
    except Exception as exc:
        logger.exception("generate_email task failed for lead=%s: %s", lead_id, exc)
        raise
