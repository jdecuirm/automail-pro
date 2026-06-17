"""Tracking pixel endpoint for email open events."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.email import Email
from app.models.lead import Lead, LeadStatus
from app.models.tracking_event import EventType, TrackingEvent
from app.utils.url_signer import verify_open_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/track", tags=["tracking"])

# Minimal valid 1×1 transparent PNG (67 bytes, spec-compliant)
TRANSPARENT_1X1_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

_PIXEL_RESPONSE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _pixel_response() -> Response:
    """Return a 1×1 transparent PNG with no-cache headers."""
    return Response(
        content=TRANSPARENT_1X1_PNG,
        media_type="image/png",
        headers=_PIXEL_RESPONSE_HEADERS,
    )


async def _load_lead_and_email(
    lead_id: uuid.UUID,
    email_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[Lead, Email] | None:
    """Fetch lead and email rows by ID.

    Args:
        lead_id: UUID of the lead to load.
        email_id: UUID of the email to load.
        session: Active database session.

    Returns:
        ``(Lead, Email)`` tuple if both exist, otherwise ``None``.
    """
    lead = (await session.execute(select(Lead).where(Lead.id == lead_id))).scalar_one_or_none()
    email = (await session.execute(select(Email).where(Email.id == email_id))).scalar_one_or_none()
    if lead is None or email is None:
        return None
    return lead, email


@router.get("/open/{token}")
async def track_open(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Record an email open event and return a 1×1 transparent PNG.

    Always returns 200 with the pixel — never breaks email rendering.
    Open events are deduplicated: only one ``TrackingEvent`` is recorded per
    ``(email_id, lead_id)`` pair regardless of how many times the pixel loads.

    Args:
        token: HMAC-signed URL-safe base64 token encoding lead_id and email_id.
        request: Incoming HTTP request (used for client IP and User-Agent).
        session: Injected async database session.
        settings: Application settings (provides HMAC secret).

    Returns:
        1×1 transparent PNG response with no-cache headers.
    """
    # Decode and verify token — return pixel immediately on any failure
    try:
        lead_id, email_id = verify_open_token(
            token, settings.tracking_secret_key.get_secret_value()
        )
    except ValueError:
        logger.warning("track_open: invalid token received")
        return _pixel_response()

    # Load lead and email rows
    result = await _load_lead_and_email(lead_id, email_id, session)
    if result is None:
        logger.warning(
            "track_open: lead or email not found lead=%s email=%s",
            lead_id,
            email_id,
        )
        return _pixel_response()

    lead, email = result

    # Dedup: skip if an open event already exists for this (email, lead) pair
    existing = (
        await session.execute(
            select(TrackingEvent).where(
                TrackingEvent.email_id == email_id,
                TrackingEvent.lead_id == lead_id,
                TrackingEvent.event_type == EventType.open,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        return _pixel_response()

    # Record the new open event — log UUIDs only, never PII
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    event = TrackingEvent(
        email_id=email_id,
        lead_id=lead_id,
        event_type=EventType.open,
        ip_address=ip,
        user_agent=ua,
    )
    session.add(event)

    # Advance lead status: sent → opened (guard against other status values)
    if lead.status == LeadStatus.sent:
        lead.status = LeadStatus.opened

    await session.commit()
    logger.info("track_open: recorded open lead=%s email=%s", lead_id, email_id)

    return _pixel_response()
