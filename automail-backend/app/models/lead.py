from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.email import Email
    from app.models.lead_research import LeadResearch
    from app.models.tracking_event import TrackingEvent


class LeadStatus(str, enum.Enum):
    uploaded = "uploaded"
    scraping = "scraping"
    researched = "researched"
    generating = "generating"
    drafted = "drafted"
    approved = "approved"
    rejected = "rejected"
    sending = "sending"
    sent = "sent"
    opened = "opened"
    failed = "failed"


class Lead(BaseModel):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_campaign_id_status", "campaign_id", "status"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(320), index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, name="lead_status"),
        default=LeadStatus.uploaded,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    campaign: Mapped[Campaign] = relationship("Campaign", back_populates="leads")
    research: Mapped[LeadResearch | None] = relationship(
        "LeadResearch", back_populates="lead", uselist=False
    )
    email_draft: Mapped[Email | None] = relationship("Email", back_populates="lead", uselist=False)
    tracking_events: Mapped[list[TrackingEvent]] = relationship(
        "TrackingEvent", back_populates="lead"
    )
