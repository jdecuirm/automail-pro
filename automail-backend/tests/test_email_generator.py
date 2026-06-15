"""Tests for email generation pipeline (Claude API mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

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
