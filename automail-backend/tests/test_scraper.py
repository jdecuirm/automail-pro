"""Tests for static scraper, robots checker, rate limiter, cache, and orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.schemas.scrape_result import ScrapeResult
from app.services import robots_checker
from app.services.scraper_exceptions import (
    ScraperBlockedError,
    ScraperNotHtmlError,
    ScraperTimeoutError,
)
from app.services.static_scraper import scrape_static

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SIMPLE_HTML = """
<html>
<head>
  <title>Acme Corp</title>
  <meta name="description" content="We build widgets">
  <meta property="og:title" content="Acme OG Title">
  <meta property="og:description" content="OG description">
</head>
<body>
  <h1>Welcome to Acme</h1>
  <h2>Our Products</h2>
  <p>Contact us at hello@acme.com for more info.</p>
  <a href="https://linkedin.com/company/acme">LinkedIn</a>
  <a href="https://github.com/acme">GitHub</a>
</body>
</html>
"""

SETTINGS_UA = "AutoMailPro/1.0 (+https://github.com/jdecuirm/automail-pro)"


def _mock_transport(
    html: str, status: int = 200, content_type: str = "text/html"
) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, text=html, headers={"content-type": content_type})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# Static scraper
# ---------------------------------------------------------------------------


async def test_static_scraper_basic():
    transport = _mock_transport(SIMPLE_HTML)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        result = await scrape_static("https://acme.com", SETTINGS_UA)

    assert result.title == "Acme Corp"
    assert result.meta_description == "We build widgets"
    assert result.og_title == "Acme OG Title"
    assert result.og_description == "OG description"
    assert "Welcome to Acme" in result.headings
    assert result.scraper_used == "static"


async def test_static_scraper_extracts_emails():
    transport = _mock_transport(SIMPLE_HTML)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        result = await scrape_static("https://acme.com", SETTINGS_UA)

    assert "hello@acme.com" in result.contact_emails


async def test_static_scraper_extracts_social_links():
    transport = _mock_transport(SIMPLE_HTML)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        result = await scrape_static("https://acme.com", SETTINGS_UA)

    assert "linkedin" in result.social_links
    assert "github" in result.social_links


async def test_static_scraper_meta_tags():
    html = """<html><head>
    <meta name="keywords" content="widgets, gadgets">
    <meta property="og:title" content="OG Title">
    </head><body><p>content</p></body></html>"""
    transport = _mock_transport(html)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        result = await scrape_static("https://example.com", SETTINGS_UA)

    assert result.meta_keywords == "widgets, gadgets"
    assert result.og_title == "OG Title"


async def test_static_scraper_403_raises_blocked():
    transport = _mock_transport("Forbidden", status=403)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        with pytest.raises(ScraperBlockedError):
            await scrape_static("https://acme.com", SETTINGS_UA)


async def test_static_scraper_429_raises_blocked():
    transport = _mock_transport("Rate limited", status=429)
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        with pytest.raises(ScraperBlockedError):
            await scrape_static("https://acme.com", SETTINGS_UA)


async def test_static_scraper_timeout_raises():
    async def _raise(_req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    with patch(
        "app.services.static_scraper.httpx.AsyncClient",
        return_value=httpx.AsyncClient(transport=httpx.MockTransport(_raise)),
    ):
        with pytest.raises(ScraperTimeoutError):
            await scrape_static("https://acme.com", SETTINGS_UA)


async def test_static_scraper_non_html_content_type():
    transport = _mock_transport('{"key": "val"}', content_type="application/json")
    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        with pytest.raises(ScraperNotHtmlError):
            await scrape_static("https://api.example.com/data", SETTINGS_UA)


# ---------------------------------------------------------------------------
# Robots checker
# ---------------------------------------------------------------------------


async def test_robots_allowed():
    robots_checker.clear_cache()

    robots_txt = "User-agent: *\nAllow: /"

    async def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=robots_txt)

    with patch("app.services.robots_checker.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(200, text=robots_txt))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        allowed = await robots_checker.is_allowed("https://acme.com/page", SETTINGS_UA)

    assert allowed is True
    robots_checker.clear_cache()


async def test_robots_disallowed():
    robots_checker.clear_cache()

    robots_txt = "User-agent: *\nDisallow: /"

    with patch("app.services.robots_checker.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(200, text=robots_txt))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        allowed = await robots_checker.is_allowed("https://blocked.com/page", SETTINGS_UA)

    assert allowed is False
    robots_checker.clear_cache()


async def test_robots_404_defaults_allow():
    robots_checker.clear_cache()

    with patch("app.services.robots_checker.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(404, text="Not Found"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        allowed = await robots_checker.is_allowed("https://norobots.com/page", SETTINGS_UA)

    assert allowed is True
    robots_checker.clear_cache()


async def test_robots_403_defaults_deny():
    robots_checker.clear_cache()

    with patch("app.services.robots_checker.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=httpx.Response(403, text="Forbidden"))
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        allowed = await robots_checker.is_allowed("https://hostile.com/page", SETTINGS_UA)

    assert allowed is False
    robots_checker.clear_cache()


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


async def test_rate_limiter_first_call_no_wait():
    """SET NX succeeds on first call → no sleep, proceed immediately."""
    from app.services import rate_limiter

    sleep_calls: list[float] = []

    async def _fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)  # NX succeeds immediately
    mock_redis.aclose = AsyncMock()

    with patch("app.services.rate_limiter.aioredis.from_url", return_value=mock_redis):
        with patch("app.services.rate_limiter.asyncio.sleep", side_effect=_fake_sleep):
            await rate_limiter.wait_for_slot("https://newdomain.com/page")

    assert sleep_calls == []
    mock_redis.set.assert_called_once()


async def test_rate_limiter_within_interval_waits():
    """SET NX fails (key exists) → fetch TTL, sleep, then retry succeeds."""
    from app.services import rate_limiter

    sleep_calls: list[float] = []

    async def _fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    mock_redis = AsyncMock()
    # First SET NX fails (domain was just requested), second succeeds after wait
    mock_redis.set = AsyncMock(side_effect=[None, True])
    mock_redis.pttl = AsyncMock(return_value=1500)  # 1.5s remaining
    mock_redis.aclose = AsyncMock()

    with patch("app.services.rate_limiter.aioredis.from_url", return_value=mock_redis):
        with patch("app.services.rate_limiter.asyncio.sleep", side_effect=_fake_sleep):
            await rate_limiter.wait_for_slot("https://recent.com/page", min_interval_seconds=2)

    assert len(sleep_calls) == 1
    assert sleep_calls[0] == pytest.approx(1.5)


async def test_rate_limiter_after_interval_no_wait():
    """SET NX succeeds when key has expired (interval elapsed) → no sleep."""
    from app.services import rate_limiter

    sleep_calls: list[float] = []

    async def _fake_sleep(s: float) -> None:
        sleep_calls.append(s)

    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)  # key expired, NX succeeds
    mock_redis.aclose = AsyncMock()

    with patch("app.services.rate_limiter.aioredis.from_url", return_value=mock_redis):
        with patch("app.services.rate_limiter.asyncio.sleep", side_effect=_fake_sleep):
            await rate_limiter.wait_for_slot("https://old.com/page", min_interval_seconds=2)

    assert sleep_calls == []


# ---------------------------------------------------------------------------
# Scrape cache
# ---------------------------------------------------------------------------


async def test_cache_miss_returns_none():
    from app.services import scrape_cache

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.aclose = AsyncMock()

    with patch("app.services.scrape_cache.aioredis.from_url", return_value=mock_redis):
        result = await scrape_cache.get_cached("https://miss.com")

    assert result is None


async def test_cache_hit_returns_scrape_result():
    from app.services import scrape_cache

    stored = ScrapeResult(url="https://hit.com", title="Hit", main_text="hello")
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=stored.model_dump_json())
    mock_redis.aclose = AsyncMock()

    with patch("app.services.scrape_cache.aioredis.from_url", return_value=mock_redis):
        result = await scrape_cache.get_cached("https://hit.com")

    assert result is not None
    assert result.title == "Hit"


async def test_cache_set_stores_with_ttl():
    from app.services import scrape_cache

    stored = ScrapeResult(url="https://store.com", title="Stored")
    mock_redis = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.aclose = AsyncMock()

    with patch("app.services.scrape_cache.aioredis.from_url", return_value=mock_redis):
        await scrape_cache.set_cached("https://store.com", stored)

    mock_redis.set.assert_called_once()
    call_kwargs = mock_redis.set.call_args
    assert call_kwargs.kwargs.get("ex") == 7 * 86400  # 7 days default


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def test_orchestrator_full_flow_success(transactional_session):
    """Lead with website → scraping succeeds → status=researched, LeadResearch created."""
    import uuid

    # Create a campaign + lead in the test DB
    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import scraper_orchestrator

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Test Campaign",
        status=CampaignStatus.scraping,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Alice",
        email="alice@acme.com",
        website="https://acme.com",
        status=LeadStatus.uploaded,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    good_result = ScrapeResult(
        url="https://acme.com", title="Acme Corp", main_text="We build things"
    )

    with patch("app.services.scraper_orchestrator.scrape_cache.get_cached", return_value=None):
        with patch(
            "app.services.scraper_orchestrator.robots_checker.is_allowed", return_value=True
        ):
            with patch(
                "app.services.scraper_orchestrator.rate_limiter.wait_for_slot",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.scraper_orchestrator.scrape_static",
                    new_callable=AsyncMock,
                    return_value=good_result,
                ):
                    with patch(
                        "app.services.scraper_orchestrator.scrape_cache.set_cached",
                        new_callable=AsyncMock,
                    ):
                        research = await scraper_orchestrator.scrape_lead(
                            lead.id, transactional_session
                        )

    assert research is not None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.researched


async def test_orchestrator_robots_blocked(transactional_session):
    """robots.txt disallows → lead.status=failed."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import scraper_orchestrator

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Robots Test",
        status=CampaignStatus.scraping,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Bob",
        email="bob@blocked.com",
        website="https://blocked.com",
        status=LeadStatus.uploaded,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    with patch("app.services.scraper_orchestrator.scrape_cache.get_cached", return_value=None):
        with patch(
            "app.services.scraper_orchestrator.robots_checker.is_allowed", return_value=False
        ):
            research = await scraper_orchestrator.scrape_lead(lead.id, transactional_session)

    assert research is None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.failed
    assert lead.error_message is not None
    assert "robots_disallowed" in lead.error_message


async def test_orchestrator_no_website_skips_to_linkedin(transactional_session):
    """Lead without website but with company LinkedIn → scraped via LinkedIn path."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import scraper_orchestrator

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="LinkedIn Test",
        status=CampaignStatus.scraping,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Carol",
        email="carol@company.com",
        website=None,
        linkedin_url="https://linkedin.com/company/some-company",
        status=LeadStatus.uploaded,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    li_result = ScrapeResult(
        url="https://linkedin.com/company/some-company",
        title="Some Company | LinkedIn",
        main_text="We are a company",
    )

    with patch("app.services.scraper_orchestrator.scrape_cache.get_cached", return_value=None):
        with patch(
            "app.services.scraper_orchestrator.robots_checker.is_allowed", return_value=True
        ):
            with patch(
                "app.services.scraper_orchestrator.rate_limiter.wait_for_slot",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.scraper_orchestrator.scrape_static",
                    new_callable=AsyncMock,
                    return_value=li_result,
                ):
                    with patch(
                        "app.services.scraper_orchestrator.scrape_cache.set_cached",
                        new_callable=AsyncMock,
                    ):
                        research = await scraper_orchestrator.scrape_lead(
                            lead.id, transactional_session
                        )

    assert research is not None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.researched


async def test_orchestrator_personal_linkedin_skipped(transactional_session):
    """Personal /in/ LinkedIn URL is skipped without crashing."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import scraper_orchestrator

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Personal LinkedIn Test",
        status=CampaignStatus.scraping,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Dave",
        email="dave@personal.com",
        website=None,
        linkedin_url="https://linkedin.com/in/davepersonal",
        status=LeadStatus.uploaded,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    # No website, personal LinkedIn → both sources fail → failed
    research = await scraper_orchestrator.scrape_lead(lead.id, transactional_session)

    assert research is None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.failed


async def test_orchestrator_both_fail(transactional_session):
    """Website times out and no LinkedIn → lead.status=failed with clear error."""
    import uuid

    from app.config import get_settings
    from app.models.campaign import Campaign, CampaignStatus
    from app.models.lead import Lead, LeadStatus
    from app.services import scraper_orchestrator

    settings = get_settings()
    campaign = Campaign(
        user_id=uuid.UUID(settings.demo_user_id),
        name="Both Fail Test",
        status=CampaignStatus.scraping,
        total_leads=1,
    )
    transactional_session.add(campaign)
    await transactional_session.flush()

    lead = Lead(
        campaign_id=campaign.id,
        name="Eve",
        email="eve@dead.com",
        website="https://dead.com",
        status=LeadStatus.uploaded,
    )
    transactional_session.add(lead)
    await transactional_session.flush()

    with patch("app.services.scraper_orchestrator.scrape_cache.get_cached", return_value=None):
        with patch(
            "app.services.scraper_orchestrator.robots_checker.is_allowed", return_value=True
        ):
            with patch(
                "app.services.scraper_orchestrator.rate_limiter.wait_for_slot",
                new_callable=AsyncMock,
            ):
                with patch(
                    "app.services.scraper_orchestrator.scrape_static",
                    new_callable=AsyncMock,
                    side_effect=ScraperTimeoutError("dead.com timed out"),
                ):
                    research = await scraper_orchestrator.scrape_lead(
                        lead.id, transactional_session
                    )

    assert research is None
    await transactional_session.refresh(lead)
    assert lead.status == LeadStatus.failed
    assert lead.error_message is not None
