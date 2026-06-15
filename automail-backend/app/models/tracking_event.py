from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.email import Email
    from app.models.lead import Lead


class EventType(str, enum.Enum):
    open = "open"


class TrackingEvent(BaseModel):
    __tablename__ = "tracking_events"
    __table_args__ = (Index("ix_tracking_events_email_id_event_type", "email_id", "event_type"),)

    email_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("emails.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[EventType] = mapped_column(
        Enum(EventType, name="event_type"),
        default=EventType.open,
    )
    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    email: Mapped[Email] = relationship("Email", back_populates="tracking_events")
    lead: Mapped[Lead] = relationship("Lead", back_populates="tracking_events")
