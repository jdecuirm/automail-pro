from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.gmail_credential import GmailCredential


class User(BaseModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sender_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sender_company: Mapped[str | None] = mapped_column(String(120), nullable=True)

    campaigns: Mapped[list[Campaign]] = relationship("Campaign", back_populates="user")
    gmail_credential: Mapped[GmailCredential | None] = relationship(
        "GmailCredential", back_populates="user", uselist=False
    )
