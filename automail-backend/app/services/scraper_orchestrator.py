"""Orchestrates the full scraping pipeline for a single lead."""

from __future__ import annotations

import logging
import uuid
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead, LeadStatus
from app.models.lead_research import LeadResearch
from app.schemas.scrape_result import ScrapeResult
from app.services import rate_limiter, robots_checker, scrape_cache
from app.services.dynamic_scraper import scrape_dynamic
from app.services.scraper_exceptions import (
    RobotsDisallowedError,
    ScraperBlockedError,
    ScraperEmptyError,
    ScraperError,
    ScraperNotHtmlError,
    ScraperTimeoutError,
)
from app.services.static_scraper import scrape_static

logger = logging.getLogger(__name__)


def _is_linkedin_company(url: str) -> bool:
    """Return True only for public /company/ pages — personal /in/ pages require login."""
    parsed = urlparse(url)
    return "linkedin.com" in parsed.netloc and "/company/" in parsed.path


def _is_linkedin_personal(url: str) -> bool:
    parsed = urlparse(url)
    return "linkedin.com" in parsed.netloc and "/in/" in parsed.path


async def _scrape_url(
    url: str, user_agent: str, static_timeout: int, dynamic_timeout: int
) -> ScrapeResult:
    """Try static first, fall back to dynamic on empty/JS-detection failure."""
    cached = await scrape_cache.get_cached(url)
    if cached is not None:
        logger.info("orchestrator: cache hit for %s", url)
        return cached

    allowed = await robots_checker.is_allowed(url, user_agent)
    if not allowed:
        raise RobotsDisallowedError(f"robots.txt disallows {url}")

    await rate_limiter.wait_for_slot(url)

    result: ScrapeResult | None = None
    try:
        result = await scrape_static(url, user_agent, timeout=static_timeout)
        if not result.main_text.strip():
            raise ScraperEmptyError("Static scraper returned empty body")
    except (ScraperEmptyError, ScraperNotHtmlError) as exc:
        logger.info("orchestrator: static empty/not-html for %s (%s) — trying Playwright", url, exc)
        result = await scrape_dynamic(url, user_agent, timeout=dynamic_timeout)

    await scrape_cache.set_cached(url, result)
    return result


async def scrape_lead(lead_id: uuid.UUID, session: AsyncSession) -> LeadResearch | None:
    """Full pipeline: load lead → scrape → persist LeadResearch → update status."""
    from app.config import get_settings

    settings = get_settings()

    stmt = select(Lead).where(Lead.id == lead_id)
    lead: Lead | None = (await session.execute(stmt)).scalar_one_or_none()
    if lead is None:
        logger.error("orchestrator: lead %s not found", lead_id)
        return None

    lead.status = LeadStatus.scraping
    await session.flush()

    website_result: ScrapeResult | None = None
    linkedin_result: ScrapeResult | None = None
    failure_reason: str | None = None

    # --- Scrape website ---
    if lead.website:
        try:
            website_result = await _scrape_url(
                lead.website,
                settings.scrape_user_agent,
                settings.scrape_static_timeout,
                settings.scrape_dynamic_timeout,
            )
        except RobotsDisallowedError:
            logger.info("orchestrator: robots blocked lead=%s url=%s", lead_id, lead.website)
            failure_reason = f"robots_disallowed: {lead.website}"
        except ScraperBlockedError as exc:
            logger.warning("orchestrator: blocked lead=%s url=%s: %s", lead_id, lead.website, exc)
            failure_reason = f"scraper_blocked: {lead.website}"
        except ScraperTimeoutError:
            logger.warning("orchestrator: timeout lead=%s url=%s", lead_id, lead.website)
            failure_reason = f"timeout: {lead.website}"
        except ScraperError as exc:
            logger.warning(
                "orchestrator: scraper error lead=%s url=%s: %s", lead_id, lead.website, exc
            )
            failure_reason = str(exc)

    # --- Scrape LinkedIn (company pages only) ---
    if lead.linkedin_url:
        if _is_linkedin_personal(lead.linkedin_url):
            logger.info(
                "orchestrator: skipping personal LinkedIn /in/ for lead=%s (requires login)",
                lead_id,
            )
        elif _is_linkedin_company(lead.linkedin_url):
            try:
                linkedin_result = await _scrape_url(
                    lead.linkedin_url,
                    settings.scrape_user_agent,
                    settings.scrape_static_timeout,
                    settings.scrape_dynamic_timeout,
                )
            except (
                RobotsDisallowedError,
                ScraperBlockedError,
                ScraperTimeoutError,
                ScraperError,
            ) as exc:
                logger.info("orchestrator: linkedin scrape failed lead=%s: %s", lead_id, exc)
        else:
            logger.info(
                "orchestrator: unrecognised linkedin URL pattern, skipping lead=%s", lead_id
            )

    # --- Persist results ---
    if website_result is None and linkedin_result is None:
        lead.status = LeadStatus.failed
        lead.error_message = failure_reason or "No content could be scraped"
        await session.commit()
        logger.warning("orchestrator: lead=%s → failed (%s)", lead_id, lead.error_message)
        return None

    primary = website_result or linkedin_result
    if primary is None:
        raise ScraperError("Invariant violated: primary result is None after content check")

    extracted: dict = primary.to_extracted_data()
    if linkedin_result and website_result:
        extracted["linkedin"] = linkedin_result.to_extracted_data()

    summary_parts: list[str] = []
    if website_result:
        summary_parts.append(f"[Website] {website_result.build_summary()}")
    if linkedin_result:
        summary_parts.append(f"[LinkedIn] {linkedin_result.build_summary()}")
    summary = "\n\n".join(summary_parts)

    research = LeadResearch(
        lead_id=lead.id,
        raw_html=primary.raw_html,
        summary=summary,
        extracted_data=extracted,
    )
    session.add(research)
    lead.status = LeadStatus.researched
    lead.error_message = None
    await session.commit()

    logger.info(
        "orchestrator: lead=%s → researched (website=%s linkedin=%s)",
        lead_id,
        website_result is not None,
        linkedin_result is not None,
    )
    return research
