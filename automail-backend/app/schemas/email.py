from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from app.models.email import EmailStatus

if TYPE_CHECKING:
    from app.models.email import Email


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: str
    lead_email: str
    lead_company: str | None = None
    subject: str
    body_text: str
    body_html: str
    status: EmailStatus
    sent_at: datetime | None = None
    gmail_message_id: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class EmailUpdateRequest(BaseModel):
    subject: str | None = None
    body_html: str | None = None
    body_text: str | None = None


class BulkSendResponse(BaseModel):
    dispatched: int
    blocked_by_quota: int
    remaining_quota_today: int


def email_to_response(email: "Email") -> EmailResponse:
    """Build an EmailResponse from an Email ORM object with loaded lead relationship."""
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
