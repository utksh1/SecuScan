"""
Tests for TLS certificate verification behaviour.

Verifies that:
  - Settings.verify_ssl defaults to True
  - SECUSCAN_VERIFY_SSL env var overrides the default
  - crawler.crawl_target passes settings.verify_ssl to httpx.AsyncClient
  - APIScanner passes settings.verify_ssl to httpx.AsyncClient
  - XSSValidationScanner passes settings.verify_ssl to httpx.AsyncClient
  - NetworkVulnerabilityScanner._probe_http passes settings.verify_ssl to httpx.AsyncClient
"""

from __future__ import annotations

import importlib
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Settings defaults
# ---------------------------------------------------------------------------


class TestSettingsVerifySslDefault:
    def test_default_is_true(self):
        from backend.secuscan.config import Settings

        s = Settings()
        assert s.verify_ssl is True

    def test_env_override_false(self, monkeypatch):
        monkeypatch.setenv("SECUSCAN_VERIFY_SSL", "false")
        from backend.secuscan.config import Settings

        s = Settings()
        assert s.verify_ssl is False

    def test_env_override_true(self, monkeypatch):
        monkeypatch.setenv("SECUSCAN_VERIFY_SSL", "true")
        from backend.secuscan.config import Settings

        s = Settings()
        assert s.verify_ssl is True


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


class _MockStreamContextManager:
    """Mimics httpx's ``client.stream(...)`` return value.

    ``AsyncClient.stream()`` is a *synchronous* call that returns an async
    context manager (it is not itself a coroutine) — the response is only
    produced on ``__aenter__``. A plain ``AsyncMock`` attribute would make
    ``client.stream(...)`` return a coroutine instead, which blows up with
    "'coroutine' object does not support the asynchronous context manager
    protocol" the moment ``crawl_target`` does ``async with client.stream(...)``.
    """

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_mock_stream_response(body: bytes = b"<html></html>", url: str = "https://example.com/"):
    async def _aiter_bytes():
        yield body

    mock_response = MagicMock()
    mock_response.url = url
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.history = []
    mock_response.aiter_bytes = MagicMock(return_value=_aiter_bytes())
    return mock_response


class TestCrawlerVerifySsl:
    @pytest.mark.asyncio
    async def test_crawl_target_passes_verify_ssl(self):
        mock_response = _make_mock_stream_response()

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=_MockStreamContextManager(mock_response))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.crawler.settings") as mock_settings:
                mock_settings.verify_ssl = True
                from backend.secuscan.crawler import crawl_target

                await crawl_target("https://example.com")

                mock_cls.assert_called_once()
                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is True

    @pytest.mark.asyncio
    async def test_crawl_target_verify_ssl_false_when_disabled(self):
        mock_response = _make_mock_stream_response()

        mock_client = AsyncMock()
        mock_client.stream = MagicMock(return_value=_MockStreamContextManager(mock_response))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.crawler.settings") as mock_settings:
                mock_settings.verify_ssl = False
                from backend.secuscan.crawler import crawl_target

                await crawl_target("https://example.com")

                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is False


# ---------------------------------------------------------------------------
# API Scanner
# ---------------------------------------------------------------------------


class TestAPIScannerVerifySsl:
    @pytest.mark.asyncio
    async def test_api_scanner_passes_verify_ssl(self):
        from backend.secuscan.scanners.api_scanner import APIScanner

        scanner = APIScanner("task-verify", None)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text="", headers={}))
        mock_client.stream = MagicMock(
            return_value=_MockStreamContextManager(_make_mock_stream_response())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.api_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.api_scanner.settings") as mock_settings:
                with patch("backend.secuscan.scanners.api_scanner.crawl_target", return_value={"api_hints": []}):
                    mock_settings.verify_ssl = True
                    with patch.object(scanner, "_fetch_spec", return_value=None):
                        with patch.object(scanner, "_probe_graphql", return_value=([], [])):
                            await scanner.run("https://example.com", {})

                            mock_cls.assert_called()
                            _, kwargs = mock_cls.call_args
                            assert kwargs["verify"] is True

    @pytest.mark.asyncio
    async def test_api_scanner_verify_ssl_false_when_disabled(self):
        from backend.secuscan.scanners.api_scanner import APIScanner

        scanner = APIScanner("task-no-verify", None)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=MagicMock(status_code=404, text="", headers={}))
        mock_client.stream = MagicMock(
            return_value=_MockStreamContextManager(_make_mock_stream_response())
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.api_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.api_scanner.settings") as mock_settings:
                with patch("backend.secuscan.scanners.api_scanner.crawl_target", return_value={"api_hints": []}):
                    mock_settings.verify_ssl = False
                    with patch.object(scanner, "_fetch_spec", return_value=None):
                        with patch.object(scanner, "_probe_graphql", return_value=([], [])):
                            await scanner.run("https://example.com", {})

                            _, kwargs = mock_cls.call_args
                            assert kwargs["verify"] is False


# ---------------------------------------------------------------------------
# XSS Validation Scanner
# ---------------------------------------------------------------------------


class TestXSSScannerVerifySsl:
    @pytest.mark.asyncio
    async def test_xss_scanner_passes_verify_ssl(self):
        from backend.secuscan.scanners.xss_validation_scanner import XSSValidationScanner

        scanner = XSSValidationScanner("task-xss", None)

        mock_response = MagicMock()
        mock_response.text = ""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.xss_validation_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.xss_validation_scanner.settings") as mock_settings:
                mock_settings.verify_ssl = True
                await scanner.run("https://example.com/?q=test", {"timeout": 5})

                mock_cls.assert_called_once()
                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is True

    @pytest.mark.asyncio
    async def test_xss_scanner_verify_ssl_false_when_disabled(self):
        from backend.secuscan.scanners.xss_validation_scanner import XSSValidationScanner

        scanner = XSSValidationScanner("task-xss-noverify", None)

        mock_response = MagicMock()
        mock_response.text = ""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.xss_validation_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.xss_validation_scanner.settings") as mock_settings:
                mock_settings.verify_ssl = False
                await scanner.run("https://example.com/?q=test", {"timeout": 5})

                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is False


# ---------------------------------------------------------------------------
# Network Vulnerability Scanner
# ---------------------------------------------------------------------------


class TestNetworkVulnScannerVerifySsl:
    @pytest.mark.asyncio
    async def test_probe_http_passes_verify_ssl(self):
        from backend.secuscan.scanners.network_vulnerability_scanner import NetworkVulnerabilityScanner

        scanner = NetworkVulnerabilityScanner("task-net", None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test</title></html>"
        mock_response.headers = {"server": "nginx"}
        mock_response.url = "https://192.168.1.1:443/"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.network_vulnerability_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.network_vulnerability_scanner.settings") as mock_settings:
                mock_settings.verify_ssl = True
                result = await scanner._probe_http("192.168.1.1", 443, tls=True)

                mock_cls.assert_called_once()
                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is True
                assert result is not None

    @pytest.mark.asyncio
    async def test_probe_http_verify_ssl_false_when_disabled(self):
        from backend.secuscan.scanners.network_vulnerability_scanner import NetworkVulnerabilityScanner

        scanner = NetworkVulnerabilityScanner("task-net-nv", None)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><title>Test</title></html>"
        mock_response.headers = {"server": "nginx"}
        mock_response.url = "https://192.168.1.1:443/"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("backend.secuscan.scanners.network_vulnerability_scanner.httpx.AsyncClient", return_value=mock_client) as mock_cls:
            with patch("backend.secuscan.scanners.network_vulnerability_scanner.settings") as mock_settings:
                mock_settings.verify_ssl = False
                result = await scanner._probe_http("192.168.1.1", 443, tls=True)

                _, kwargs = mock_cls.call_args
                assert kwargs["verify"] is False
                assert result is not None


# ---------------------------------------------------------------------------
# No hardcoded verify=False remains
# ---------------------------------------------------------------------------


class TestNoHardcodedVerifyFalse:
    """Ensure no httpx.AsyncClient call in the patched files still uses verify=False."""

    def _scan_file(self, path: str) -> list[str]:
        violations = []
        with open(path) as f:
            for i, line in enumerate(f, 1):
                stripped = line.strip()
                if "AsyncClient" in stripped and "verify=False" in stripped:
                    violations.append(f"{path}:{i}: {stripped}")
        return violations

    def test_crawler_no_hardcoded_verify_false(self):
        from backend.secuscan import crawler

        violations = self._scan_file(crawler.__file__)
        assert violations == [], f"Hardcoded verify=False found: {violations}"

    def test_api_scanner_no_hardcoded_verify_false(self):
        from backend.secuscan.scanners import api_scanner

        violations = self._scan_file(api_scanner.__file__)
        assert violations == [], f"Hardcoded verify=False found: {violations}"

    def test_xss_scanner_no_hardcoded_verify_false(self):
        from backend.secuscan.scanners import xss_validation_scanner

        violations = self._scan_file(xss_validation_scanner.__file__)
        assert violations == [], f"Hardcoded verify=False found: {violations}"

    def test_network_vuln_scanner_no_hardcoded_verify_false(self):
        from backend.secuscan.scanners import network_vulnerability_scanner

        violations = self._scan_file(network_vulnerability_scanner.__file__)
        assert violations == [], f"Hardcoded verify=False found: {violations}"
