"""Email management endpoints — approve, reject, edit, and retrieve emails."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user_id
from app.database import get_db
from app.limiter import limit_emails_approve, limiter
from app.models.email import Email, EmailStatus
from app.models.lead import Lead, LeadStatus
from app.schemas.email import EmailResponse, EmailUpdateRequest, email_to_response
from app.services.campaign_advance import complete_campaign_if_done

router = APIRouter(prefix="/api/emails", tags=["emails"])


async def _get_email_owned(
    email_id: uuid.UUID,
    session: AsyncSession,
    user_id: uuid.UUID,
) -> Email:
    """Load email + lead + campaign. Raises 404 if not found or wrong owner."""
    email: Email | None = (
        await session.execute(
            select(Email)
            .options(selectinload(Email.lead).selectinload(Lead.campaign))
            .where(Email.id == email_id)
        )
    ).scalar_one_or_none()

    if email is None or email.lead.campaign.user_id != user_id:
        raise HTTPException(status_code=404, detail="Email not found.")

    return email


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> EmailResponse:
    """Get a single email draft with full detail."""
    email = await _get_email_owned(email_id, session, user_id)
    return email_to_response(email)


@router.post("/{email_id}/approve", response_model=EmailResponse)
@limiter.limit(limit_emails_approve)
async def approve_email(
    request: Request,
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> EmailResponse:
    """Mark a draft email as approved. Sending is triggered separately via bulk-send."""
    email = await _get_email_owned(email_id, session, user_id)

    if email.status not in (EmailStatus.draft, EmailStatus.rejected):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve email with status '{email.status.value}'.",
        )

    email.status = EmailStatus.approved
    email.lead.status = LeadStatus.approved
    await session.commit()
    await session.refresh(email, attribute_names=["updated_at"])

    return email_to_response(email)


@router.post("/{email_id}/reject", response_model=EmailResponse)
async def reject_email(
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> EmailResponse:
    """Reject a draft email — it will not be sent."""
    email = await _get_email_owned(email_id, session, user_id)

    if email.status not in (EmailStatus.draft, EmailStatus.approved):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot reject email with status '{email.status.value}'.",
        )

    email.status = EmailStatus.rejected
    email.lead.status = LeadStatus.rejected
    await complete_campaign_if_done(email.lead.campaign_id, session)
    await session.commit()
    await session.refresh(email, attribute_names=["updated_at"])

    return email_to_response(email)


@router.patch("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: uuid.UUID,
    body: EmailUpdateRequest,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> EmailResponse:
    """Edit subject/body of a draft email. Only allowed when status=draft."""
    email = await _get_email_owned(email_id, session, user_id)

    if email.status != EmailStatus.draft:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot edit email with status '{email.status.value}'. "
                "Only draft emails can be edited."
            ),
        )

    if body.subject is not None:
        email.subject = body.subject
    if body.body_html is not None:
        email.body_html = body.body_html
    if body.body_text is not None:
        email.body_text = body.body_text

    await session.commit()
    await session.refresh(email, attribute_names=["updated_at"])
    return email_to_response(email)
