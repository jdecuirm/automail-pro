"""Per-domain async rate limiter backed by Redis."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

import redis.asyncio as aioredis

from app.config import get_settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "scrape:lastreq:"


def _domain_key(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc or url
    return f"{_KEY_PREFIX}{domain}"


async def wait_for_slot(url: str, min_interval_seconds: int | None = None) -> None:
    """Block until a rate-limit slot is available for *url*'s domain, then claim it.

    Uses Redis SET NX (atomic set-if-not-exists) so concurrent workers on the
    same domain cannot both proceed simultaneously — only one wins the slot and
    the other waits for the TTL to expire before retrying.
    """
    settings = get_settings()
    interval = (
        min_interval_seconds
        if min_interval_seconds is not None
        else settings.scrape_rate_limit_seconds
    )
    key = _domain_key(url)
    interval_ms = interval * 1000

    client: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    try:
        while True:
            # Atomically claim the slot: succeeds only if no request was made
            # within the last interval. The key expires after 2× interval as a safety net.
            acquired = await client.set(key, "1", nx=True, px=interval_ms * 2)
            if acquired:
                break

            # Slot taken — wait out the remaining TTL then retry
            ttl_ms = await client.pttl(key)
            wait_s = max(ttl_ms, 50) / 1000  # floor at 50 ms to avoid tight spin
            logger.debug("rate_limiter: domain=%s waiting %.2fs for slot", key, wait_s)
            await asyncio.sleep(wait_s)
    finally:
        await client.aclose()
