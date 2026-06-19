"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid

from fastapi import Depends

from app.config import Settings, get_settings


def get_current_user_id(settings: Settings = Depends(get_settings)) -> uuid.UUID:
    """Return the current user UUID. Swap this for JWT logic when auth is real."""
    return uuid.UUID(settings.demo_user_id)
