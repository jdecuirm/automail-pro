"""Google OAuth 2.0 callback and credential management endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_id
from app.config import Settings, get_settings
from app.database import get_db
from app.limiter import limit_oauth_authorize, limiter
from app.models.gmail_credential import GmailCredential
from app.services import google_oauth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth/google", tags=["oauth"])


class OAuthStatusResponse(BaseModel):
    connected: bool
    email_address: str | None = None
    needs_reconnect: bool = False


@router.get("/authorize")
@limiter.limit(limit_oauth_authorize)
async def authorize(
    request: Request,
    settings: Settings = Depends(get_settings),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    state = google_oauth.sign_state(str(user_id), settings.app_secret_key.get_secret_value())
    auth_url = await google_oauth.build_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> RedirectResponse:
    """Handle Google's OAuth callback: verify state, exchange code, store tokens."""
    frontend_url = settings.frontend_base_url

    if error or not code or not state:
        reason = error or "missing_code_or_state"
        logger.warning("oauth_callback: denied or missing params — %s", reason)
        return RedirectResponse(url=f"{frontend_url}?oauth_error={reason}")

    try:
        google_oauth.verify_state(state, settings.app_secret_key.get_secret_value())
    except ValueError as exc:
        logger.warning("oauth_callback: invalid state — %s", exc)
        return RedirectResponse(url=f"{frontend_url}?oauth_error=invalid_state")

    try:
        tokens = await google_oauth.exchange_code_for_tokens(code, state=state)
    except Exception as exc:
        logger.error("oauth_callback: token exchange failed — %s", exc)
        return RedirectResponse(url=f"{frontend_url}?oauth_error=token_exchange_failed")

    await google_oauth.store_gmail_credential(session, user_id, tokens)
    logger.info("oauth_callback: gmail connected for user=%s", user_id)
    return RedirectResponse(url=f"{frontend_url}?oauth_success=true")


@router.get("/status", response_model=OAuthStatusResponse)
async def status(
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> OAuthStatusResponse:
    """Return the OAuth connection status for the demo user."""
    credential = (
        await session.execute(select(GmailCredential).where(GmailCredential.user_id == user_id))
    ).scalar_one_or_none()

    if credential is None:
        return OAuthStatusResponse(connected=False)

    try:
        email = credential.get_email_address()
    except Exception:
        email = None

    return OAuthStatusResponse(
        connected=True,
        email_address=email,
        needs_reconnect=credential.needs_reconnect,
    )


@router.delete("/disconnect", status_code=204)
async def disconnect(
    session: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete the stored Gmail credential for the demo user."""
    credential = (
        await session.execute(select(GmailCredential).where(GmailCredential.user_id == user_id))
    ).scalar_one_or_none()

    if credential is None:
        raise HTTPException(status_code=404, detail="No Gmail credential found.")

    await session.delete(credential)
    await session.commit()
    logger.info("oauth: credential deleted for user=%s", user_id)
