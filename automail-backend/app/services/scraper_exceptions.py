"""Custom exceptions for the scraping pipeline."""

from __future__ import annotations


class ScraperError(Exception):
    """Base class for all scraper errors."""


class ScraperBlockedError(ScraperError):
    """Received HTTP 403 / 429 — the server rejected the request."""


class ScraperTimeoutError(ScraperError):
    """Request timed out."""


class ScraperEmptyError(ScraperError):
    """Response returned but no usable content was found."""


class ScraperNotHtmlError(ScraperError):
    """Response content-type is not text/html."""


class RobotsDisallowedError(ScraperError):
    """robots.txt explicitly disallows scraping this URL."""
