"""Celery task: generate email draft for a single lead via Claude."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="leads.generate", bind=True, max_retries=2)
def generate_email(self: Any, lead_id: str) -> dict[str, Any]:
    """Generate a personalized email draft via Claude and persist it."""
    from app.database import get_session_context
    from app.services import email_generator

    lead_uuid = uuid.UUID(lead_id)

    async def _run() -> dict[str, Any]:
        async with get_session_context() as session:
            email = await email_generator.generate_email_draft(lead_uuid, session)
            return {
                "lead_id": lead_id,
                "status": "drafted" if email else "failed",
                "email_id": str(email.id) if email else None,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("generate_email task failed for lead=%s: %s", lead_id, exc)
        raise
