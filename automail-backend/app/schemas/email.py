from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.email import EmailStatus


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_id: uuid.UUID
    lead_name: str
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
