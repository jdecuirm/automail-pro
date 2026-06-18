"""Email management endpoints — approve, reject, edit, and retrieve emails."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models.email import Email, EmailStatus
from app.models.lead import Lead, LeadStatus
from app.schemas.email import EmailResponse, EmailUpdateRequest
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


def _to_response(email: Email) -> EmailResponse:
    # Manual dict required: EmailResponse.lead_name has no direct ORM column.
    return EmailResponse.model_validate(
        {
            "id": email.id,
            "lead_id": email.lead_id,
            "lead_name": email.lead.name,
            "lead_email": email.lead.email,
            "lead_company": email.lead.company,
            "subject": email.subject,
            "body_text": email.body_text,
            "body_html": email.body_html,
            "status": email.status,
            "sent_at": email.sent_at,
            "gmail_message_id": email.gmail_message_id,
            "error_message": email.error_message,
            "created_at": email.created_at,
            "updated_at": email.updated_at,
        }
    )


@router.get("/{email_id}", response_model=EmailResponse)
async def get_email(
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailResponse:
    """Get a single email draft with full detail."""
    user_id = uuid.UUID(settings.demo_user_id)
    email = await _get_email_owned(email_id, session, user_id)
    return _to_response(email)


@router.post("/{email_id}/approve", response_model=EmailResponse)
async def approve_email(
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailResponse:
    """Mark a draft email as approved. Sending is triggered separately via bulk-send."""
    user_id = uuid.UUID(settings.demo_user_id)
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

    return _to_response(email)


@router.post("/{email_id}/reject", response_model=EmailResponse)
async def reject_email(
    email_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailResponse:
    """Reject a draft email — it will not be sent."""
    user_id = uuid.UUID(settings.demo_user_id)
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

    return _to_response(email)


@router.patch("/{email_id}", response_model=EmailResponse)
async def update_email(
    email_id: uuid.UUID,
    body: EmailUpdateRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> EmailResponse:
    """Edit subject/body of a draft email. Only allowed when status=draft."""
    user_id = uuid.UUID(settings.demo_user_id)
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
    return _to_response(email)
