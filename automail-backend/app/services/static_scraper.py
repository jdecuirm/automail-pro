"""Async HTTP scraper using httpx + BeautifulSoup4."""

from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from app.schemas.scrape_result import ScrapeResult
from app.services.scraper_exceptions import (
    ScraperBlockedError,
    ScraperNotHtmlError,
    ScraperTimeoutError,
)

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SOCIAL_DOMAINS = {
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "github.com": "github",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "youtube.com": "youtube",
}

_SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}


def _extract_text(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(_SKIP_TAGS):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s{2,}", " ", text)[:5000]


def _extract_meta(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": name})
    if isinstance(tag, Tag):
        content = tag.get("content")
        if isinstance(content, str):
            return content.strip() or None
    return None


def _extract_og(soup: BeautifulSoup, prop: str) -> str | None:
    tag = soup.find("meta", attrs={"property": prop})
    if isinstance(tag, Tag):
        content = tag.get("content")
        if isinstance(content, str):
            return content.strip() or None
    return None


def _extract_social_links(soup: BeautifulSoup, base_url: str) -> dict[str, str]:
    links: dict[str, str] = {}
    for a_tag in soup.find_all("a", href=True):
        if not isinstance(a_tag, Tag):
            continue
        href = a_tag.get("href", "")
        if not isinstance(href, str):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        for domain, key in _SOCIAL_DOMAINS.items():
            if domain in parsed.netloc and key not in links:
                links[key] = absolute
    return links


def _extract_emails(text: str) -> list[str]:
    found = _EMAIL_RE.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for e in found:
        low = e.lower()
        if low not in seen:
            seen.add(low)
            result.append(low)
    return result[:10]


def _extract_headings(soup: BeautifulSoup) -> list[str]:
    headings: list[str] = []
    for tag in soup.find_all(["h1", "h2"]):
        if not isinstance(tag, Tag):
            continue
        text = tag.get_text(strip=True)
        if text:
            headings.append(text)
        if len(headings) >= 5:
            break
    return headings


def _parse_html(url: str, html: str, scraper_used: str = "static") -> ScrapeResult:
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if isinstance(title_tag, Tag) else None

    main_text = _extract_text(BeautifulSoup(html, "lxml"))

    return ScrapeResult(
        url=url,
        title=title,
        meta_description=_extract_meta(soup, "description"),
        meta_keywords=_extract_meta(soup, "keywords"),
        og_title=_extract_og(soup, "og:title"),
        og_description=_extract_og(soup, "og:description"),
        headings=_extract_headings(soup),
        main_text=main_text,
        contact_emails=_extract_emails(main_text),
        social_links=_extract_social_links(soup, url),
        raw_html=html[:50_000],
        scraper_used=scraper_used,
    )


async def scrape_static(url: str, user_agent: str, timeout: int = 15) -> ScrapeResult:
    """Fetch *url* with httpx and parse HTML. Raises on error conditions."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            max_redirects=5,
            verify=True,
        ) as client:
            resp = await client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise ScraperTimeoutError(f"Timeout fetching {url}") from exc
    except httpx.RequestError as exc:
        raise ScraperTimeoutError(f"Network error fetching {url}: {exc}") from exc

    if resp.status_code in (403, 429):
        raise ScraperBlockedError(f"HTTP {resp.status_code} from {url}")

    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ScraperBlockedError(f"HTTP {exc.response.status_code} from {url}") from exc

    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type and "html" not in content_type:
        raise ScraperNotHtmlError(f"Unexpected content-type {content_type!r} for {url}")

    logger.info(
        "static_scraper: fetched %s status=%d size=%d", url, resp.status_code, len(resp.text)
    )
    return _parse_html(url, resp.text, scraper_used="static")
