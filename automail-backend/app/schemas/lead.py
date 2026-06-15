from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.lead import LeadStatus


class LeadCreate(BaseModel):
    name: str
    email: str
    company: str | None = None
    website: str | None = None
    linkedin_url: str | None = None


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    company: str | None
    website: str | None
    linkedin_url: str | None
    status: LeadStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class LeadPagination(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
