from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.lead import Lead
    from app.models.user import User


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scraping = "scraping"
    generating = "generating"
    review = "review"
    sending = "sending"
    completed = "completed"
    paused = "paused"


class Campaign(BaseModel):
    __tablename__ = "campaigns"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        default=CampaignStatus.draft,
    )
    csv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_leads: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    user: Mapped[User] = relationship("User", back_populates="campaigns")
    leads: Mapped[list[Lead]] = relationship("Lead", back_populates="campaign")
