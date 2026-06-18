from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.campaign import CampaignStatus


class CampaignListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: CampaignStatus
    total_leads: int
    csv_filename: str | None = None
    created_at: datetime
    updated_at: datetime


class CampaignStats(BaseModel):
    uploaded: int = 0
    scraping: int = 0
    researched: int = 0
    generating: int = 0
    drafted: int = 0
    approved: int = 0
    rejected: int = 0
    sending: int = 0
    sent: int = 0
    opened: int = 0
    failed: int = 0


class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: CampaignStatus
    csv_filename: str | None
    total_leads: int
    stats: CampaignStats
    created_at: datetime
    updated_at: datetime
