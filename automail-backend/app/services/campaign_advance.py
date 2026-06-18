"""Campaign status advancement utilities — shared between task and API layers."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus

logger = logging.getLogger(__name__)

# Statuses that mean "still in flight" — a lead in any of these has not
# reached a terminal state and the campaign cannot advance yet.
PENDING_LEAD_STATUSES = frozenset(
    [LeadStatus.uploaded, LeadStatus.scraping, LeadStatus.researched, LeadStatus.generating]
)


async def advance_campaign_if_done(lead: Lead, session: AsyncSession) -> None:
    """Transition campaign → 'review' once no leads remain in-progress.

    Safe to call at any terminal point (drafted, failed from scraping,
    failed from generation). Idempotent — does nothing if the campaign is
    already in 'review' or 'completed'.

    After setting 'review', also checks whether the campaign should jump
    straight to 'completed' (edge case: all leads failed, no emails created).
    """
    pending: int = (
        await session.execute(
            select(func.count())
            .select_from(Lead)
            .where(Lead.campaign_id == lead.campaign_id)
            .where(Lead.status.in_(PENDING_LEAD_STATUSES))
        )
    ).scalar_one()

    if pending > 0:
        return

    campaign: Campaign | None = await session.get(Campaign, lead.campaign_id)
    if campaign and campaign.status not in (CampaignStatus.review, CampaignStatus.completed):
        campaign.status = CampaignStatus.review
        logger.info(
            "campaign_advance: campaign=%s → review (all leads processed)",
            lead.campaign_id,
        )
        # Edge case: every lead failed scraping — no emails were ever created.
        # Zero active emails → skip straight to completed.
        await complete_campaign_if_done(lead.campaign_id, session)


async def complete_campaign_if_done(campaign_id: uuid.UUID, session: AsyncSession) -> None:
    """Transition campaign → 'completed' when no emails remain in an actionable state.

    Actionable states: draft, approved, sending — still need user or system action.
    Terminal states (sent, opened, failed, rejected) no longer block completion.

    Safe to call after every email terminal transition. Idempotent.
    """
    from app.models.email import Email, EmailStatus

    active_count: int = (
        await session.execute(
            select(func.count())
            .select_from(Email)
            .join(Lead, Email.lead_id == Lead.id)
            .where(Lead.campaign_id == campaign_id)
            .where(Email.status.in_([EmailStatus.draft, EmailStatus.approved, EmailStatus.sending]))
        )
    ).scalar_one()

    if active_count > 0:
        return

    campaign: Campaign | None = await session.get(Campaign, campaign_id)
    if campaign and campaign.status == CampaignStatus.review:
        campaign.status = CampaignStatus.completed
        logger.info(
            "campaign_advance: campaign=%s → completed (no active emails remaining)",
            campaign_id,
        )
