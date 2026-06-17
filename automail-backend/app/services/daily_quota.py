"""Daily email send quota enforcement."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.campaign import Campaign
from app.models.email import Email, EmailStatus
from app.models.lead import Lead


async def _count_sent_today(user_id: uuid.UUID, session: AsyncSession) -> int:
    """Count emails with status=sent for a specific user today (UTC midnight boundary).

    Args:
        user_id: The user whose sent emails to count.
        session: Active async database session.

    Returns:
        Number of emails sent by the user since UTC midnight today.
    """
    today_midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    stmt = (
        select(func.count())
        .select_from(Email)
        .join(Lead, Email.lead_id == Lead.id)
        .join(Campaign, Lead.campaign_id == Campaign.id)
        .where(
            Campaign.user_id == user_id,
            Email.status == EmailStatus.sent,
            Email.sent_at >= today_midnight,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def can_send(user_id: uuid.UUID, session: AsyncSession) -> bool:
    """Return True if the user has not reached the daily send quota.

    Args:
        user_id: The user to check quota for.
        session: Active async database session.

    Returns:
        True if the user can still send emails today, False if quota is exhausted.
    """
    limit = get_settings().max_emails_per_user_per_day
    sent_today = await _count_sent_today(user_id, session)
    return sent_today < limit


async def remaining_quota(user_id: uuid.UUID, session: AsyncSession) -> int:
    """Return the number of emails the user can still send today.

    Args:
        user_id: The user to check quota for.
        session: Active async database session.

    Returns:
        Remaining send slots (0 if quota is exhausted, never negative).
    """
    limit = get_settings().max_emails_per_user_per_day
    sent_today = await _count_sent_today(user_id, session)
    return max(0, limit - sent_today)
