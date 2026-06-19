"""Async robots.txt checker with per-domain in-process cache."""

from __future__ import annotations

import logging
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)

# Simple in-process cache: domain -> (RobotFileParser | None)
# None means either no robots.txt (allow), fetch error (allow), or 403 deny
_cache: dict[str, RobotFileParser | None] = {}

_ROBOTS_TIMEOUT = 5.0  # seconds


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def _fetch_robots(base_url: str, user_agent: str) -> RobotFileParser | None:
    robots_url = f"{base_url.rstrip('/')}/robots.txt"
    try:
        async with httpx.AsyncClient(timeout=_ROBOTS_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(robots_url, headers={"User-Agent": user_agent})
    except httpx.TimeoutException:
        logger.warning("robots_checker: timeout fetching %s — defaulting to allow", robots_url)
        return None  # allow on timeout
    except Exception as exc:
        logger.warning("robots_checker: error fetching %s: %s — allowing", robots_url, exc)
        return None

    if resp.status_code == 404:
        return None  # no robots.txt → allow
    if resp.status_code == 403:
        logger.info("robots_checker: 403 on %s — treating as deny", robots_url)
        return None
    if resp.status_code != 200:
        logger.warning(
            "robots_checker: unexpected status %d for %s — allowing", resp.status_code, robots_url
        )
        return None

    parser = RobotFileParser()
    parser.parse(resp.text.splitlines())
    return parser


def _product_token(user_agent: str) -> str:
    """Extract the product token from a full User-Agent string.

    RobotFileParser.can_fetch() matches against the product token in User-agent:
    directives, not the full UA string. e.g. "AutoMailPro/1.0 (+url)" -> "AutoMailPro/1.0".
    """
    return user_agent.split()[0] if user_agent else user_agent


async def is_allowed(url: str, user_agent: str) -> bool:
    """Return True if the given URL may be fetched per robots.txt."""
    base = _domain(url)
    if base not in _cache:
        _cache[base] = await _fetch_robots(base, user_agent)

    entry = _cache[base]
    if entry is None:
        return True

    token = _product_token(user_agent)
    allowed: bool = entry.can_fetch(token, url)
    if not allowed:
        logger.info("robots_checker: robots.txt disallows %s for agent %r", url, token)
    return allowed


def clear_cache() -> None:
    """Reset the in-process robots cache (useful in tests)."""
    _cache.clear()
