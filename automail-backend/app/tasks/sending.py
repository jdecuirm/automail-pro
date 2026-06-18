"""Celery task: send an approved email via the user's Gmail account."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.celery_app import celery_app
from app.services.gmail_sender import CredentialRevokedError, GmailRateLimitedError

logger = logging.getLogger(__name__)


@celery_app.task(
    name="emails.send",
    bind=True,
    max_retries=5,
    autoretry_for=(GmailRateLimitedError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_email_task(self: Any, email_id: str) -> dict[str, Any]:
    """Send a single approved email via Gmail API.

    Returns:
        dict with keys: email_id, status ("sent" | "failed" | "skipped"),
        gmail_message_id (str | None), reason (str | None).
    """

    from sqlalchemy.orm import selectinload

    from app.config import get_settings as _get_settings
    from app.database import get_task_session
    from app.models.email import Email, EmailStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import daily_quota, gmail_sender
    from app.services.campaign_advance import complete_campaign_if_done
    from app.utils.url_signer import sign_open_token

    email_uuid = uuid.UUID(email_id)

    async def _run() -> dict[str, Any]:
        async with get_task_session() as session:
            email: Email | None = (
                await session.execute(
                    select(Email)
                    .options(selectinload(Email.lead).selectinload(Lead.campaign))
                    .where(Email.id == email_uuid)
                )
            ).scalar_one_or_none()

            if email is None:
                logger.error("send_email_task: email %s not found", email_id)
                return {
                    "email_id": email_id,
                    "status": "failed",
                    "gmail_message_id": None,
                    "reason": "email_not_found",
                }

            if email.status != EmailStatus.approved:
                logger.warning(
                    "send_email_task: email %s status=%s expected approved — skipping",
                    email_id,
                    email.status,
                )
                return {
                    "email_id": email_id,
                    "status": "skipped",
                    "gmail_message_id": None,
                    "reason": f"unexpected_status:{email.status.value}",
                }

            user_id = email.lead.campaign.user_id
            campaign_id = email.lead.campaign_id

            if not await daily_quota.can_send(user_id, session):
                logger.warning("send_email_task: quota exceeded user=%s", user_id)
                email.status = EmailStatus.failed
                email.error_message = "daily_quota_exceeded"
                await complete_campaign_if_done(campaign_id, session)
                await session.commit()
                return {
                    "email_id": email_id,
                    "status": "failed",
                    "gmail_message_id": None,
                    "reason": "daily quota exceeded",
                }

            email.status = EmailStatus.sending
            await session.commit()

            # Inject tracking pixel into HTML
            _settings = _get_settings()
            _pixel_token = sign_open_token(
                email.lead_id, email.id, _settings.tracking_secret_key.get_secret_value()
            )
            _pixel_url = f"{_settings.app_base_url}/api/track/open/{_pixel_token}"
            _pixel_tag = (
                f'<img src="{_pixel_url}" width="1" height="1" '
                'style="display:none;border:0;outline:0;text-decoration:none" alt="">'
            )
            _html = email.body_html or ""
            _html, _n_replaced = re.subn(
                r"</body>", f"{_pixel_tag}</body>", _html, count=1, flags=re.IGNORECASE
            )
            if _n_replaced == 0:
                _html = _html + _pixel_tag

            try:
                gmail_id = await gmail_sender.send_email(
                    user_id=user_id,
                    to=email.lead.email,
                    subject=email.subject,
                    body_html=_html,
                    body_text=email.body_text,
                    session=session,
                )
            except CredentialRevokedError:
                logger.error("send_email_task: credential revoked user=%s", user_id)
                email.status = EmailStatus.failed
                email.error_message = "credential_revoked"
                await complete_campaign_if_done(campaign_id, session)
                await session.commit()
                return {
                    "email_id": email_id,
                    "status": "failed",
                    "gmail_message_id": None,
                    "reason": "credential revoked — user must reconnect gmail",
                }
            except GmailRateLimitedError:
                email.status = EmailStatus.approved  # revert for retry
                await session.commit()
                raise  # autoretry_for triggers retry with backoff
            except Exception as exc:
                logger.exception("send_email_task: unexpected error email=%s", email_id)
                email.status = EmailStatus.failed
                email.error_message = str(exc)[:500]
                await complete_campaign_if_done(campaign_id, session)
                await session.commit()
                raise

            email.status = EmailStatus.sent
            email.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
            email.gmail_message_id = gmail_id
            email.lead.status = LeadStatus.sent
            await complete_campaign_if_done(campaign_id, session)
            await session.commit()

            logger.info("send_email_task: sent email=%s gmail_id=%s", email_id, gmail_id)
            return {
                "email_id": email_id,
                "status": "sent",
                "gmail_message_id": gmail_id,
                "reason": None,
            }

    return asyncio.run(_run())
