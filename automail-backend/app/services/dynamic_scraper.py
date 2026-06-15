"""Playwright-based fallback scraper for JS-heavy pages."""

from __future__ import annotations

import logging

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

from app.schemas.scrape_result import ScrapeResult
from app.services.scraper_exceptions import ScraperEmptyError, ScraperTimeoutError
from app.services.static_scraper import _parse_html

logger = logging.getLogger(__name__)


async def scrape_dynamic(url: str, user_agent: str, timeout: int = 30) -> ScrapeResult:
    """Render *url* in headless Chromium and parse the resulting HTML."""
    timeout_ms = timeout * 1000
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
        )
        page = await context.new_page()
        try:
            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            except PlaywrightTimeout as exc:
                raise ScraperTimeoutError(f"Playwright timeout on {url}") from exc

            html = await page.content()
            if not html or len(html.strip()) < 200:
                raise ScraperEmptyError(f"Playwright got empty content for {url}")

            logger.info("dynamic_scraper: rendered %s html_len=%d", url, len(html))
            return _parse_html(url, html, scraper_used="dynamic")
        finally:
            await context.close()
            await browser.close()
