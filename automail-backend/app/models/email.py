from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.tracking_event import TrackingEvent


class EmailStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    rejected = "rejected"
    sending = "sending"
    sent = "sent"
    failed = "failed"


class Email(BaseModel):
    __tablename__ = "emails"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), unique=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(998))
    body_html: Mapped[str] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, name="email_status"),
        default=EmailStatus.draft,
    )
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    lead: Mapped[Lead] = relationship("Lead", back_populates="email_draft")
    tracking_events: Mapped[list[TrackingEvent]] = relationship(
        "TrackingEvent", back_populates="email"
    )
