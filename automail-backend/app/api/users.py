"""User profile endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        sender_name=user.sender_name,
        sender_company=user.sender_company,
        profile_complete=bool(user.sender_name and user.sender_company),
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> UserProfileResponse:
    """Return the current user's sender profile."""
    user: User | None = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return _to_response(user)


@router.patch("/me", response_model=UserProfileResponse)
async def update_profile(
    body: UserProfileUpdate,
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> UserProfileResponse:
    """Update the current user's sender name and company."""
    user: User | None = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    if body.sender_name is not None:
        user.sender_name = body.sender_name.strip() or None
    if body.sender_company is not None:
        user.sender_company = body.sender_company.strip() or None

    await session.commit()
    await session.refresh(user)
    return _to_response(user)
