from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.campaign import Campaign, CampaignStatus
from app.models.email import Email
from app.models.lead import Lead, LeadStatus
from app.schemas.campaign import CampaignListItem, CampaignResponse, CampaignStats
from app.schemas.csv_upload import CSVUploadResponse
from app.schemas.email import BulkSendResponse, EmailResponse, email_to_response
from app.schemas.lead import LeadPagination, LeadResponse
from app.services.csv_parser import parse_csv
from app.services.daily_quota import remaining_quota
from app.tasks.scraping import scrape_lead
from app.tasks.sending import send_email_task

logger = logging.getLogger(__name__)


async def create_campaign_from_csv(
    session: AsyncSession,
    file_bytes: bytes,
    filename: str,
    name: str,
    user_id: uuid.UUID,
) -> CSVUploadResponse:
    """Parse CSV, persist campaign + leads, dispatch scraping tasks."""
    valid_leads, errors = parse_csv(file_bytes, filename)

    if not valid_leads:
        raise ValueError(f"No valid leads found in CSV. Rows with errors: {len(errors)}.")

    campaign = Campaign(
        user_id=user_id,
        name=name,
        csv_filename=filename,
        status=CampaignStatus.scraping,
        total_leads=len(valid_leads),
    )
    session.add(campaign)
    await session.flush()  # populate campaign.id

    leads = [
        Lead(
            campaign_id=campaign.id,
            name=lc.name,
            email=lc.email,
            company=lc.company,
            website=lc.website,
            linkedin_url=lc.linkedin_url,
            status=LeadStatus.uploaded,
        )
        for lc in valid_leads
    ]
    session.add_all(leads)
    await session.flush()  # populate lead.id values
    # Collect IDs before commit so we can dispatch tasks after the transaction is visible
    lead_ids = [str(lead.id) for lead in leads]

    await session.commit()

    # Dispatch AFTER commit so workers find the lead rows in the DB
    for lead_id in lead_ids:
        scrape_lead.delay(lead_id)
    logger.info(
        "campaign_service: created campaign=%s leads=%d filename=%r",
        campaign.id,
        len(leads),
        filename,
    )

    total_rows = len(valid_leads) + len(errors)
    return CSVUploadResponse(
        campaign_id=campaign.id,
        total_rows=total_rows,
        valid_leads=len(valid_leads),
        invalid_leads=len(errors),
        validation_errors=errors,
    )


async def list_campaigns(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[CampaignListItem]:
    stmt = select(Campaign).where(Campaign.user_id == user_id).order_by(Campaign.created_at.desc())
    result = await session.execute(stmt)
    return [CampaignListItem.model_validate(c) for c in result.scalars().all()]


async def get_campaign(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> CampaignResponse | None:
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.user_id == user_id,
    )
    campaign = (await session.execute(stmt)).scalar_one_or_none()
    if campaign is None:
        return None

    # Lazy status recalculation: if "review" but all emails are terminal, advance
    # to "completed". Self-heals campaigns where the worker missed the transition
    # (crash, restart, race condition). Cheap: complete_campaign_if_done is a no-op
    # when active emails still exist.
    if campaign.status == CampaignStatus.review:
        from app.services.campaign_advance import complete_campaign_if_done

        await complete_campaign_if_done(campaign_id, session)
        await session.commit()
        await session.refresh(campaign)

    stats_rows = (
        await session.execute(
            select(Lead.status, func.count(Lead.id))
            .where(Lead.campaign_id == campaign_id)
            .group_by(Lead.status)
        )
    ).all()
    stats_dict = {row[0].value: row[1] for row in stats_rows}
    stats = CampaignStats(
        uploaded=stats_dict.get("uploaded", 0),
        scraping=stats_dict.get("scraping", 0),
        researched=stats_dict.get("researched", 0),
        generating=stats_dict.get("generating", 0),
        drafted=stats_dict.get("drafted", 0),
        approved=stats_dict.get("approved", 0),
        rejected=stats_dict.get("rejected", 0),
        sending=stats_dict.get("sending", 0),
        sent=stats_dict.get("sent", 0),
        opened=stats_dict.get("opened", 0),
        failed=stats_dict.get("failed", 0),
    )
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        status=campaign.status,
        csv_filename=campaign.csv_filename,
        total_leads=campaign.total_leads,
        stats=stats,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


async def list_leads(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int,
    page_size: int,
) -> LeadPagination | None:
    """Return paginated leads for a campaign owned by user_id, or None if not found."""
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user_id)
        )
    ).scalar_one_or_none()
    if campaign is None:
        return None

    count_stmt = select(func.count()).select_from(Lead).where(Lead.campaign_id == campaign_id)
    total: int = (await session.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(Lead)
        .where(Lead.campaign_id == campaign_id)
        .order_by(Lead.created_at)
        .offset(offset)
        .limit(page_size)
    )
    leads = (await session.execute(stmt)).scalars().all()

    return LeadPagination(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
    )


async def list_emails(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[EmailResponse] | None:
    """Return all email drafts for leads in a campaign owned by user_id.

    Args:
        session: Async database session.
        campaign_id: UUID of the campaign.
        user_id: UUID of the requesting user (ownership check).

    Returns:
        List of EmailResponse objects, or None if campaign not found/not owned by user.
    """
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user_id)
        )
    ).scalar_one_or_none()
    if campaign is None:
        return None

    stmt = (
        select(Email)
        .join(Lead, Email.lead_id == Lead.id)
        .where(Lead.campaign_id == campaign_id)
        .options(selectinload(Email.lead))
        .order_by(Email.created_at)
    )
    emails = (await session.execute(stmt)).scalars().all()
    return [email_to_response(email) for email in emails]


async def dispatch_approved_emails(
    session: AsyncSession,
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> BulkSendResponse | None:
    """Dispatch send tasks for all approved emails in a campaign.

    Args:
        session: Async database session.
        campaign_id: UUID of the campaign to process.
        user_id: UUID of the requesting user (ownership check).

    Returns:
        BulkSendResponse with dispatch counts, or None if campaign not found.

    Raises:
        HTTPException: 422 if the sender profile is incomplete.
    """
    from fastapi import HTTPException

    from app.models.email import EmailStatus
    from app.models.user import User

    campaign = (
        await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if campaign is None:
        return None

    user: User | None = await session.get(User, user_id)
    if user is None or not (user.sender_name and user.sender_company):
        raise HTTPException(
            status_code=422,
            detail=(
                "Sender profile incomplete. "
                "Set your name and company in Settings → Account before sending."
            ),
        )

    approved_emails = (
        (
            await session.execute(
                select(Email)
                .join(Lead, Email.lead_id == Lead.id)
                .where(
                    Lead.campaign_id == campaign_id,
                    Email.status == EmailStatus.approved,
                )
            )
        )
        .scalars()
        .all()
    )

    quota_left = await remaining_quota(user_id, session)
    to_dispatch = approved_emails[:quota_left]
    blocked = approved_emails[quota_left:]

    for email in to_dispatch:
        send_email_task.delay(str(email.id))

    return BulkSendResponse(
        dispatched=len(to_dispatch),
        blocked_by_quota=len(blocked),
        remaining_quota_today=max(0, quota_left - len(to_dispatch)),
    )
