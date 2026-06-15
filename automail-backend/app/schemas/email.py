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
    created_at: datetime
    updated_at: datetime
