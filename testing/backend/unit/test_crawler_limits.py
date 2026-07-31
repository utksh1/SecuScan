"""Unit tests for verifying crawl_target max-redirects and max-size constraints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from backend.secuscan.crawler import crawl_target


@pytest.mark.asyncio
async def test_crawl_target_max_size_via_content_length():
    """Verify that crawl_target raises ValueError if the Content-Length header exceeds max_size."""
    mock_response = MagicMock()
    mock_response.headers = {"content-length": "10000000"}  # 10MB
    mock_response.status_code = 200
    mock_response.url = "http://example.com"
    mock_response.history = []

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream.return_value = mock_stream_ctx

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(ValueError, match="Response size exceeds limit"):
            await crawl_target("http://example.com", max_size=1000)


@pytest.mark.asyncio
async def test_crawl_target_max_size_via_streaming():
    """Verify that crawl_target raises ValueError if the streamed chunks exceed max_size."""
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.status_code = 200
    mock_response.url = "http://example.com"
    mock_response.history = []

    async def mock_aiter_bytes():
        yield b"hello "
        yield b"world of pentesting"

    mock_response.aiter_bytes = mock_aiter_bytes

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream.return_value = mock_stream_ctx

    with patch("httpx.AsyncClient", return_value=mock_client):
        # Setting max_size to 10 bytes:
        # First chunk (b"hello ") is 6 bytes (ok).
        # Second chunk adds 19 bytes, total 25 bytes (exceeds limit).
        with pytest.raises(ValueError, match="Response size exceeds limit"):
            await crawl_target("http://example.com", max_size=10)


@pytest.mark.asyncio
async def test_crawl_target_max_redirects_exceeded():
    """Verify that crawl_target raises httpx.TooManyRedirects when the redirect limit is hit."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_request = httpx.Request("GET", "http://example.com")

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(side_effect=httpx.TooManyRedirects("Too many redirects", request=mock_request))
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream.return_value = mock_stream_ctx

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.TooManyRedirects):
            await crawl_target("http://example.com", max_redirects=2)
