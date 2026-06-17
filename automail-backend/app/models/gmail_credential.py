from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class GmailCredential(BaseModel):
    __tablename__ = "gmail_credentials"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    encrypted_refresh_token: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_access_token: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    token_expiry: Mapped[datetime | None] = mapped_column(nullable=True)
    email_address: Mapped[bytes] = mapped_column(LargeBinary)  # Fernet-encrypted
    needs_reconnect: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    user: Mapped[User] = relationship("User", back_populates="gmail_credential")

    def get_email_address(self) -> str:
        """Decrypt and return the stored email address."""
        from app.services.encryption import decrypt_str

        return decrypt_str(self.email_address)
