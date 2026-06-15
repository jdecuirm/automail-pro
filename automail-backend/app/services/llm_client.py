"""Thin async wrapper around the Anthropic messages API."""

from __future__ import annotations

import logging

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.InternalServerError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(4),
    reraise=True,
)
async def complete(
    system: str,
    user: str,
    model: str = "claude-haiku-4-5",
    max_tokens: int = 1024,
) -> str:
    """Call Claude and return the text of the first content block."""
    from app.config import get_settings

    settings = get_settings()
    api_key = settings.anthropic_api_key
    if api_key is None:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = anthropic.AsyncAnthropic(api_key=api_key.get_secret_value())
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        raise ValueError(f"Unexpected content block type: {type(block)}")
    text: str = block.text
    logger.debug(
        "llm_client: model=%s input_tokens=%d output_tokens=%d",
        model,
        response.usage.input_tokens,
        response.usage.output_tokens,
    )
    return text
