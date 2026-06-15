"""Tests for email generation pipeline (Claude API mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.llm_client import complete


async def test_complete_returns_text():
    import anthropic

    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(spec=anthropic.types.TextBlock, text="Hello world", type="text")
    ]
    mock_response.usage = MagicMock(input_tokens=10, output_tokens=20)

    with patch("app.services.llm_client.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client

        result = await complete(
            system="You are a helpful assistant.",
            user="Say hello.",
            model="claude-haiku-4-5",
            max_tokens=100,
        )

    assert result == "Hello world"


async def test_complete_raises_when_no_api_key():
    """complete() raises ValueError when ANTHROPIC_API_KEY is not configured."""
    import pytest

    from app.config import Settings

    mock_settings = MagicMock(spec=Settings)
    mock_settings.anthropic_api_key = None

    with patch("app.config.get_settings", return_value=mock_settings):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            await complete(system="sys", user="usr")


async def test_complete_retries_on_rate_limit_error():
    """complete() retries on RateLimitError and succeeds on second attempt."""
    import anthropic
    import httpx

    from app.config import Settings

    mock_success = MagicMock()
    mock_success.content = [MagicMock(spec=anthropic.types.TextBlock, text="Retried!", type="text")]
    mock_success.usage = MagicMock(input_tokens=5, output_tokens=5)

    # Create a proper httpx.Request and Response pair
    request = httpx.Request("GET", "https://api.anthropic.com/messages")
    rate_limit_response = httpx.Response(429, content=b"rate limited", request=request)
    rate_limit_error = anthropic.RateLimitError(
        "rate limited",
        response=rate_limit_response,
        body=None,
    )

    mock_settings = MagicMock(spec=Settings)
    mock_settings.anthropic_api_key = MagicMock()
    mock_settings.anthropic_api_key.get_secret_value.return_value = "test-key"

    with patch("app.config.get_settings", return_value=mock_settings):
        with patch("app.services.llm_client.anthropic.AsyncAnthropic") as mock_cls:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(side_effect=[rate_limit_error, mock_success])
            mock_cls.return_value = mock_client

            result = await complete(system="sys", user="usr")

    assert result == "Retried!"
    assert mock_client.messages.create.call_count == 2


from app.services.email_generator import build_user_prompt, parse_claude_response


def test_build_user_prompt_includes_lead_info():
    research_summary = "Title: Acme Corp\nContent: We build widgets for SMBs."
    prompt = build_user_prompt(
        lead_name="Alice Johnson",
        company="Acme Corp",
        research_summary=research_summary,
    )
    assert "Alice Johnson" in prompt
    assert "Acme Corp" in prompt
    assert "widgets" in prompt


def test_build_user_prompt_excludes_email_address():
    """PII: lead email must NOT appear in prompt sent to Claude."""
    prompt = build_user_prompt(
        lead_name="Bob Smith",
        company="Startup",
        research_summary="Some research.",
        lead_email="bob@startup.io",
    )
    assert "bob@startup.io" not in prompt


def test_parse_claude_response_valid_json():
    raw = """```json
{
  "subject": "Quick question about Acme",
  "body_text": "Hi Alice,\n\nI noticed...\n\nBest,\nJorge",
  "body_html": "<p>Hi Alice,</p><p>I noticed...</p>"
}
```"""
    result = parse_claude_response(raw)
    assert result["subject"] == "Quick question about Acme"
    assert "Hi Alice" in result["body_text"]
    assert "<p>" in result["body_html"]


def test_parse_claude_response_plain_json():
    raw = '{"subject": "Hello", "body_text": "Hi", "body_html": "<p>Hi</p>"}'
    result = parse_claude_response(raw)
    assert result["subject"] == "Hello"


def test_parse_claude_response_missing_key_raises():
    raw = '{"subject": "Hello", "body_text": "Hi"}'  # missing body_html
    with pytest.raises(ValueError, match="body_html"):
        parse_claude_response(raw)


async def test_generate_email_draft_returns_email_model(transactional_session):
    """Full generate_email_draft() flow with mocked Claude response."""
    import uuid
    from unittest.mock import AsyncMock, patch

    from app.services.email_generator import generate_email_draft

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.models.lead_research import LeadResearch

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Gen Test",
        status=CampaignStatus.generating,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Alice Johnson",
        email="alice@acme.com",
        company="Acme Corp",
        website="https://acme.com",
        status=LeadStatus.researched,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    research = LeadResearch(
        lead_id=lead.id,
        summary="[Website] Title: Acme Corp\nContent: We build widgets.",
        extracted_data={"title": "Acme Corp"},
    )
    transactional_session.add(research)
    await transactional_session.flush()

    claude_json = (
        '{"subject": "Quick question about Acme Corp",'
        ' "body_text": "Hi Alice,\\n\\nI came across Acme Corp...",'
        ' "body_html": "<p>Hi Alice,</p><p>I came across Acme Corp...</p>"}'
    )

    with patch(
        "app.services.email_generator.complete", new_callable=AsyncMock, return_value=claude_json
    ):
        email = await generate_email_draft(lead.id, transactional_session)

    assert email is not None
    assert email.subject == "Quick question about Acme Corp"
    assert "Alice" in email.body_text
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.drafted


async def test_generate_email_draft_lead_not_found(transactional_session):
    import uuid

    from app.services.email_generator import generate_email_draft

    result = await generate_email_draft(uuid.uuid4(), transactional_session)
    assert result is None


async def test_generate_email_draft_no_research(transactional_session):
    """Lead exists but has no LeadResearch — should mark failed."""
    import uuid

    from app.services.email_generator import generate_email_draft

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="No Research Campaign",
        status=CampaignStatus.generating,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Bob Smith",
        email="bob@startup.io",
        company="Startup",
        status=LeadStatus.researched,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    result = await generate_email_draft(lead.id, transactional_session)
    assert result is None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.failed
    assert lead.error_message is not None
