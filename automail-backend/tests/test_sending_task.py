"""Tests for emails.send Celery task."""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.email import EmailStatus


def test_send_task_success_updates_email_and_lead():
    """Successful send → email.status=sent, lead.status=sent, gmail_message_id set."""
    from app.celery_app import celery_app
    from app.tasks.sending import send_email_task

    email_id = str(uuid.uuid4())
    mock_lead = MagicMock()
    mock_lead.campaign = MagicMock()
    mock_lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    mock_email = MagicMock()
    mock_email.id = uuid.UUID(email_id)
    mock_email.status = EmailStatus.approved
    mock_email.lead = mock_lead
    mock_email.subject = "Test Subject"
    mock_email.body_html = "<p>Hi</p>"
    mock_email.body_text = "Hi"

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_execute.scalar_one.return_value = 0  # complete_campaign_if_done count query
    mock_session.execute.return_value = mock_execute

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.database.get_task_session", _fake_ctx):
        with patch("app.services.gmail_sender.send_email", new_callable=AsyncMock) as mock_send:
            with patch(
                "app.services.daily_quota.can_send", new_callable=AsyncMock, return_value=True
            ):
                mock_send.return_value = "gmail-msg-id-abc"
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                try:
                    result = send_email_task.apply(args=[email_id])
                finally:
                    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "sent"
    assert data["gmail_message_id"] == "gmail-msg-id-abc"


def test_send_task_quota_exceeded_marks_failed_no_retry():
    from app.celery_app import celery_app
    from app.tasks.sending import send_email_task

    email_id = str(uuid.uuid4())
    mock_lead = MagicMock()
    mock_lead.campaign = MagicMock()
    mock_lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    mock_email = MagicMock()
    mock_email.status = EmailStatus.approved
    mock_email.lead = mock_lead

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_execute.scalar_one.return_value = 0  # complete_campaign_if_done count query
    mock_session.execute.return_value = mock_execute

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.database.get_task_session", _fake_ctx):
        with patch("app.services.daily_quota.can_send", new_callable=AsyncMock, return_value=False):
            celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
            try:
                result = send_email_task.apply(args=[email_id])
            finally:
                celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "failed"
    assert "quota" in data["reason"].lower()


def test_send_task_credential_revoked_marks_failed_no_retry():
    from app.celery_app import celery_app
    from app.services.gmail_sender import CredentialRevokedError
    from app.tasks.sending import send_email_task

    email_id = str(uuid.uuid4())
    mock_lead = MagicMock()
    mock_lead.campaign = MagicMock()
    mock_lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    mock_email = MagicMock()
    mock_email.status = EmailStatus.approved
    mock_email.lead = mock_lead
    mock_email.body_html = "<p>test</p>"

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_execute.scalar_one.return_value = 0  # complete_campaign_if_done count query
    mock_session.execute.return_value = mock_execute

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    with patch("app.database.get_task_session", _fake_ctx):
        with patch("app.services.daily_quota.can_send", new_callable=AsyncMock, return_value=True):
            with patch(
                "app.services.gmail_sender.send_email",
                new_callable=AsyncMock,
                side_effect=CredentialRevokedError("revoked"),
            ):
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                try:
                    result = send_email_task.apply(args=[email_id])
                finally:
                    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "failed"
    assert "revoked" in data["reason"].lower()


def test_send_task_injects_tracking_pixel():
    """Approved email gets tracking pixel injected into body_html before send."""
    from app.celery_app import celery_app
    from app.tasks.sending import send_email_task

    email_id = str(uuid.uuid4())
    lead_id = uuid.uuid4()

    mock_lead = MagicMock()
    mock_lead.campaign = MagicMock()
    mock_lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    mock_email = MagicMock()
    mock_email.id = uuid.UUID(email_id)
    mock_email.lead_id = lead_id
    mock_email.status = EmailStatus.approved
    mock_email.lead = mock_lead
    mock_email.subject = "Test Subject"
    mock_email.body_html = "<html><body><p>Hi there</p></body></html>"
    mock_email.body_text = "Hi there"

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_execute.scalar_one.return_value = 0  # complete_campaign_if_done count query
    mock_session.execute.return_value = mock_execute

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    captured_html: list[str] = []

    async def _capture_send(**kwargs: object) -> str:
        captured_html.append(str(kwargs.get("body_html", "")))
        return "gmail-pixel-test-id"

    with patch("app.database.get_task_session", _fake_ctx):
        with patch("app.services.gmail_sender.send_email", new=_capture_send):
            with patch(
                "app.services.daily_quota.can_send", new_callable=AsyncMock, return_value=True
            ):
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                try:
                    result = send_email_task.apply(args=[email_id])
                finally:
                    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "sent"
    assert len(captured_html) == 1
    assert "/api/track/open/" in captured_html[0]
    assert 'width="1"' in captured_html[0]
    assert captured_html[0].index("/api/track/open/") < captured_html[0].index("</body>")


def test_send_task_injects_pixel_case_insensitive_body_tag():
    """Tracking pixel is injected even when </body> tag uses uppercase letters."""
    from app.celery_app import celery_app
    from app.tasks.sending import send_email_task

    email_id = str(uuid.uuid4())
    lead_id = uuid.uuid4()

    mock_lead = MagicMock()
    mock_lead.campaign = MagicMock()
    mock_lead.campaign.user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    mock_email = MagicMock()
    mock_email.id = uuid.UUID(email_id)
    mock_email.lead_id = lead_id
    mock_email.status = EmailStatus.approved
    mock_email.lead = mock_lead
    mock_email.subject = "Test Subject"
    mock_email.body_html = "<html><body><p>Hi</p></BODY></html>"
    mock_email.body_text = "Hi"

    mock_session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_email
    mock_execute.scalar_one.return_value = 0  # complete_campaign_if_done count query
    mock_session.execute.return_value = mock_execute

    @contextlib.asynccontextmanager
    async def _fake_ctx():
        yield mock_session

    captured_html: list[str] = []

    async def _capture_send(**kwargs: object) -> str:
        captured_html.append(str(kwargs.get("body_html", "")))
        return "gmail-pixel-uppercase-id"

    with patch("app.database.get_task_session", _fake_ctx):
        with patch("app.services.gmail_sender.send_email", new=_capture_send):
            with patch(
                "app.services.daily_quota.can_send", new_callable=AsyncMock, return_value=True
            ):
                celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
                try:
                    result = send_email_task.apply(args=[email_id])
                finally:
                    celery_app.conf.update(task_always_eager=False, task_eager_propagates=False)

    data = result.get()
    assert data["status"] == "sent"
    assert len(captured_html) == 1
    assert "/api/track/open/" in captured_html[0]
