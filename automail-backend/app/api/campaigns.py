from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.campaign import Campaign
from app.models.lead import Lead
from app.schemas.campaign import CampaignListItem, CampaignResponse
from app.schemas.csv_upload import CSVUploadResponse
from app.schemas.email import BulkSendResponse, EmailResponse
from app.schemas.lead import LeadPagination
from app.services import campaign_service
from app.services.daily_quota import remaining_quota
from app.tasks.sending import send_email_task

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_ACCEPTED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


@router.post("", status_code=201, response_model=CSVUploadResponse)
async def create_campaign(
    file: UploadFile = File(..., description="CSV file with leads"),
    name: str = Form(..., min_length=1, max_length=255, description="Campaign name"),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CSVUploadResponse:
    """Upload a CSV of leads and create a new campaign."""
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in _ACCEPTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type!r}. Upload a CSV file.",
        )

    contents = await file.read()

    max_bytes = settings.csv_max_size_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.csv_max_size_mb} MB.",
        )

    filename = file.filename or "upload.csv"
    user_id = uuid.UUID(settings.demo_user_id)

    try:
        result = await campaign_service.create_campaign_from_csv(
            session, contents, filename, name, user_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return result


@router.get("", response_model=list[CampaignListItem])
async def list_campaigns(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[CampaignListItem]:
    """List all campaigns for the demo user."""
    user_id = uuid.UUID(settings.demo_user_id)
    return await campaign_service.list_campaigns(session, user_id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> CampaignResponse:
    """Get campaign detail by ID."""
    user_id = uuid.UUID(settings.demo_user_id)
    campaign = await campaign_service.get_campaign(session, campaign_id, user_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.get("/{campaign_id}/leads", response_model=LeadPagination)
async def list_campaign_leads(
    campaign_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LeadPagination:
    """List leads for a campaign with pagination."""
    user_id = uuid.UUID(settings.demo_user_id)
    result = await campaign_service.list_leads(session, campaign_id, user_id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return result


@router.get("/{campaign_id}/emails", response_model=list[EmailResponse])
async def list_campaign_emails(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[EmailResponse]:
    """List all email drafts for a campaign."""
    user_id = uuid.UUID(settings.demo_user_id)
    result = await campaign_service.list_emails(session, campaign_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return result


@router.post("/{campaign_id}/send-approved", response_model=BulkSendResponse)
async def bulk_send_approved(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> BulkSendResponse:
    """Dispatch send tasks for all approved emails in a campaign, up to daily quota."""
    from app.models.email import Email, EmailStatus

    user_id = uuid.UUID(settings.demo_user_id)

    # Raw ORM lookup — avoids CampaignResponse.model_validate so this endpoint
    # doesn't pull in the full campaign serialization path.
    campaign = (
        await session.execute(
            select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")

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
