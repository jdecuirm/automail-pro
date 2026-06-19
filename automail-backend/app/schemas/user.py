"""Pydantic schemas for user profile endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """Public profile fields returned to the frontend."""

    sender_name: str | None
    sender_company: str | None
    profile_complete: bool

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Fields accepted by PATCH /api/users/me."""

    sender_name: str | None = Field(None, max_length=120)
    sender_company: str | None = Field(None, max_length=120)
