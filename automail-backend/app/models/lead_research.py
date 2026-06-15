from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.lead import Lead


class LeadResearch(BaseModel):
    __tablename__ = "lead_research"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), unique=True, index=True
    )
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    extracted_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    scraped_at: Mapped[datetime] = mapped_column(server_default=func.now())

    lead: Mapped[Lead] = relationship("Lead", back_populates="research")
