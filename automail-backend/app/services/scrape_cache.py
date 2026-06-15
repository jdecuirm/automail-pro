"""Redis-backed cache for scrape results (TTL = 7 days by default)."""

from __future__ import annotations

import hashlib
import json
import logging

import redis.asyncio as aioredis

from app.config import get_settings
from app.schemas.scrape_result import ScrapeResult

logger = logging.getLogger(__name__)

_KEY_PREFIX = "scrape:result:"


def _url_key(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()
    return f"{_KEY_PREFIX}{digest}"


async def get_cached(url: str) -> ScrapeResult | None:
    settings = get_settings()
    client: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        raw = await client.get(_url_key(url))
        if raw is None:
            return None
        logger.debug("scrape_cache: hit for %s", url)
        return ScrapeResult.model_validate(json.loads(raw))
    except Exception as exc:
        logger.warning("scrape_cache: get error for %s: %s", url, exc)
        return None
    finally:
        await client.aclose()


async def set_cached(url: str, result: ScrapeResult) -> None:
    settings = get_settings()
    ttl_seconds = settings.scrape_cache_ttl_days * 86400
    client: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.set(_url_key(url), result.model_dump_json(), ex=ttl_seconds)
        logger.debug("scrape_cache: stored %s (ttl=%ds)", url, ttl_seconds)
    except Exception as exc:
        logger.warning("scrape_cache: set error for %s: %s", url, exc)
    finally:
        await client.aclose()


async def invalidate(url: str) -> None:
    settings = get_settings()
    client: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.delete(_url_key(url))
    finally:
        await client.aclose()
