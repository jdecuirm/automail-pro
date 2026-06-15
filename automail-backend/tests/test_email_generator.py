"""Tests for email generation pipeline (Claude API mocked)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.services.llm_client import complete


async def test_complete_returns_text():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello world")]
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
