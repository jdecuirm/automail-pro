"""Google OAuth 2.0 callback and credential management endpoints."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db
from app.models.gmail_credential import GmailCredential
from app.services import google_oauth
from app.services.encryption import encrypt_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/oauth/google", tags=["oauth"])


class OAuthStatusResponse(BaseModel):
    connected: bool
    email_address: str | None = None
    needs_reconnect: bool = False


@router.get("/authorize")
async def authorize(
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    """Redirect the user to Google's OAuth consent screen."""
    user_id = settings.demo_user_id
    state = google_oauth.sign_state(user_id, settings.app_secret_key.get_secret_value())
    auth_url = google_oauth.build_auth_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
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
        tokens = google_oauth.exchange_code_for_tokens(code)
    except Exception as exc:
        logger.error("oauth_callback: token exchange failed — %s", exc)
        return RedirectResponse(url=f"{frontend_url}?oauth_error=token_exchange_failed")

    user_id = uuid.UUID(settings.demo_user_id)
    encrypted_refresh = encrypt_str(tokens["refresh_token"])
    encrypted_access = encrypt_str(tokens["access_token"])
    encrypted_email = encrypt_str(tokens["email"])

    # Upsert: one credential row per user
    existing = (
        await session.execute(select(GmailCredential).where(GmailCredential.user_id == user_id))
    ).scalar_one_or_none()

    if existing:
        existing.encrypted_refresh_token = encrypted_refresh
        existing.encrypted_access_token = encrypted_access
        existing.token_expiry = tokens["expiry"]
        existing.email_address = encrypted_email
        existing.needs_reconnect = False
    else:
        session.add(
            GmailCredential(
                user_id=user_id,
                encrypted_refresh_token=encrypted_refresh,
                encrypted_access_token=encrypted_access,
                token_expiry=tokens["expiry"],
                email_address=encrypted_email,
                needs_reconnect=False,
            )
        )

    await session.commit()
    logger.info("oauth_callback: gmail connected for user=%s email=%s", user_id, tokens["email"])
    return RedirectResponse(url=f"{frontend_url}?oauth_success=true")


@router.get("/status", response_model=OAuthStatusResponse)
async def status(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> OAuthStatusResponse:
    """Return the OAuth connection status for the demo user."""
    user_id = uuid.UUID(settings.demo_user_id)
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
    settings: Settings = Depends(get_settings),
) -> None:
    """Delete the stored Gmail credential for the demo user."""
    user_id = uuid.UUID(settings.demo_user_id)
    credential = (
        await session.execute(select(GmailCredential).where(GmailCredential.user_id == user_id))
    ).scalar_one_or_none()

    if credential is None:
        raise HTTPException(status_code=404, detail="No Gmail credential found.")

    await session.delete(credential)
    await session.commit()
    logger.info("oauth: credential deleted for user=%s", user_id)
