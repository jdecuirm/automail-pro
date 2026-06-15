from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign, CampaignStatus
from app.models.email import Email
from app.models.lead import Lead, LeadStatus
from app.schemas.campaign import CampaignListItem, CampaignResponse
from app.schemas.csv_upload import CSVUploadResponse
from app.schemas.email import EmailResponse
from app.schemas.lead import LeadPagination, LeadResponse
from app.services.csv_parser import parse_csv
from app.tasks.scraping import scrape_lead

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
    return CampaignResponse.model_validate(campaign)


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
        select(Email, Lead.name.label("lead_name"))
        .join(Lead, Email.lead_id == Lead.id)
        .where(Lead.campaign_id == campaign_id)
        .order_by(Email.created_at)
    )
    rows = (await session.execute(stmt)).all()

    results: list[EmailResponse] = []
    for email, lead_name in rows:
        data = EmailResponse.model_validate(
            {
                "id": email.id,
                "lead_id": email.lead_id,
                "lead_name": lead_name,
                "subject": email.subject,
                "body_text": email.body_text,
                "body_html": email.body_html,
                "status": email.status,
                "created_at": email.created_at,
                "updated_at": email.updated_at,
            }
        )
        results.append(data)
    return results
