from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.config import Settings, get_settings
from app.database import get_db
from app.limiter import limit_campaigns_create, limiter
from app.models.campaign import Campaign
from app.schemas.campaign import CampaignListItem, CampaignResponse
from app.schemas.csv_upload import CSVUploadResponse
from app.schemas.email import BulkSendResponse, EmailResponse
from app.schemas.lead import LeadPagination
from app.services import campaign_service

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

_ACCEPTED_CONTENT_TYPES = {
    "text/csv",
    "text/plain",
    "application/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


@router.post("", status_code=201, response_model=CSVUploadResponse)
@limiter.limit(limit_campaigns_create)
async def create_campaign(
    request: Request,
    file: UploadFile = File(..., description="CSV file with leads"),
    name: str = Form(..., min_length=1, max_length=255, description="Campaign name"),
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user_id: uuid.UUID = Depends(get_current_user_id),
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
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[CampaignListItem]:
    """List all campaigns for the demo user."""
    return await campaign_service.list_campaigns(session, user_id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CampaignResponse:
    """Get campaign detail by ID."""
    campaign = await campaign_service.get_campaign(session, campaign_id, user_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def delete_campaign(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a campaign and all its leads, emails, and research (cascade)."""
    exists = (
        await session.execute(
            select(Campaign.id).where(Campaign.id == campaign_id, Campaign.user_id == user_id)
        )
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    await session.execute(delete(Campaign).where(Campaign.id == campaign_id))
    await session.commit()


@router.get("/{campaign_id}/leads", response_model=LeadPagination)
async def list_campaign_leads(
    campaign_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> LeadPagination:
    """List leads for a campaign with pagination."""
    result = await campaign_service.list_leads(session, campaign_id, user_id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return result


@router.get("/{campaign_id}/emails", response_model=list[EmailResponse])
async def list_campaign_emails(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[EmailResponse]:
    """List all email drafts for a campaign."""
    result = await campaign_service.list_emails(session, campaign_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return result


@router.post("/{campaign_id}/send-approved", response_model=BulkSendResponse)
async def bulk_send_approved(
    campaign_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> BulkSendResponse:
    """Dispatch send tasks for all approved emails in a campaign, up to daily quota."""
    result = await campaign_service.dispatch_approved_emails(session, campaign_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return result
