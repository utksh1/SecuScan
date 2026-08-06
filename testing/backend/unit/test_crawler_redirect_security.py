"""
Unit tests for the crawler redirect security controls added for issue #2369.

Verifies that crawl_target:
  - re-validates every redirect hop against the network policy before fetching it,
  - strips operator-supplied credentials (Authorization / extra headers and
    session cookies) on cross-origin redirects, and
  - keeps credentials only for same-origin hops, mirroring browser behavior.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.secuscan.crawler import (
    _check_hop_egress,
    _is_in_mandatory_denylist,
    _origin_of,
    crawl_target,
)


# ---------------------------------------------------------------------------
# Fakes used to drive crawl_target without real HTTP I/O
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, url, status_code=200, headers=None, body=b"<html></html>"):
        self.url = url
        self.status_code = status_code
        self.headers = headers or {}
        self.history = []
        self._body = body

    async def aiter_bytes(self):
        yield self._body


class _FakeStreamCM:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        return _FakeStreamCM(self._responses[url])


def _patch_client(client):
    return patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=client)


def _patch_hop_validation(allowed, reason=""):
    return patch(
        "backend.secuscan.crawler._validate_hop_target",
        new=AsyncMock(return_value=(allowed, reason)),
    )


# ---------------------------------------------------------------------------
# _origin_of
# ---------------------------------------------------------------------------


class TestOriginOf:
    def test_default_https_port_normalized(self):
        assert _origin_of("https://example.com/") == ("https", "example.com", 443)

    def test_default_http_port_normalized(self):
        assert _origin_of("http://example.com/") == ("http", "example.com", 80)

    def test_explicit_port_preserved(self):
        assert _origin_of("https://example.com:8443/x") == ("https", "example.com", 8443)

    def test_scheme_change_is_cross_origin(self):
        assert _origin_of("http://example.com/") != _origin_of("https://example.com/")

    def test_host_change_is_cross_origin(self):
        assert _origin_of("https://example.com/") != _origin_of("https://evil.example/")

    def test_non_http_scheme_uses_zero_port(self):
        assert _origin_of("file:///etc/passwd") == ("file", "", 0)


# ---------------------------------------------------------------------------
# _is_in_mandatory_denylist
# ---------------------------------------------------------------------------


class TestMandatoryDenylist:
    def test_private_rfc1918_blocked(self):
        assert _is_in_mandatory_denylist("10.0.0.5") is True
        assert _is_in_mandatory_denylist("192.168.1.1") is True

    def test_cloud_metadata_blocked(self):
        assert _is_in_mandatory_denylist("169.254.169.254") is True

    def test_loopback_blocked(self):
        assert _is_in_mandatory_denylist("127.0.0.1") is True

    def test_public_ip_allowed(self):
        assert _is_in_mandatory_denylist("8.8.8.8") is False


# ---------------------------------------------------------------------------
# _check_hop_egress
# ---------------------------------------------------------------------------


class TestCheckHopEgress:
    def test_rejects_unsupported_scheme(self):
        allowed, reason = _check_hop_egress("file:///etc/passwd")
        assert not allowed
        assert "scheme" in reason

    def test_rejects_missing_host(self):
        allowed, _ = _check_hop_egress("https:///just/a/path")
        assert not allowed

    def test_policy_engine_controls_decision(self):
        engine = MagicMock()
        engine.validate_egress_target.return_value = (False, "Denied by allowlist")
        with patch("backend.secuscan.crawler.settings.enforce_network_policy", True):
            with patch("backend.secuscan.network_policy.get_policy_engine", return_value=engine):
                allowed, reason = _check_hop_egress("https://evil.example/collect")
        assert not allowed
        assert "Denied by allowlist" in reason

    def test_policy_engine_allows_public_destination(self):
        engine = MagicMock()
        engine.validate_egress_target.return_value = (True, "")
        with patch("backend.secuscan.crawler.settings.enforce_network_policy", True):
            with patch("backend.secuscan.network_policy.get_policy_engine", return_value=engine):
                allowed, _ = _check_hop_egress("https://example.com/")
        assert allowed is True

    def test_policy_disabled_blocks_mandatory_denylist(self):
        with patch("backend.secuscan.crawler.settings.enforce_network_policy", False):
            allowed, _ = _check_hop_egress("http://10.0.0.5/")
            assert not allowed

    def test_policy_disabled_allows_public_destination(self):
        with patch("backend.secuscan.crawler.settings.enforce_network_policy", False):
            allowed, _ = _check_hop_egress("http://8.8.8.8/")
            assert allowed is True


# ---------------------------------------------------------------------------
# crawl_target redirect handling
# ---------------------------------------------------------------------------


class TestCrawlTargetRedirectSecurity:
    @pytest.mark.asyncio
    async def test_cross_origin_redirect_strips_credentials(self):
        seed = "https://example.com/"
        redirect_to = "https://evil.example/collect"
        client = _FakeClient(
            {
                seed: _FakeResponse(seed, status_code=302, headers={"location": redirect_to}),
                redirect_to: _FakeResponse(redirect_to, status_code=200, headers={}),
            }
        )
        with _patch_client(client):
            with _patch_hop_validation(True):
                result = await crawl_target(
                    seed,
                    cookies={"session": "s3cret"},
                    extra_headers={"Authorization": "Basic dXNlcjpwYXNz", "X-Api-Key": "k3y"},
                )

        assert result["final_url"] == redirect_to
        first, second = client.calls
        assert first["url"] == seed
        assert first["kwargs"]["headers"]["Authorization"] == "Basic dXNlcjpwYXNz"
        assert first["kwargs"]["headers"]["X-Api-Key"] == "k3y"
        assert first["kwargs"]["cookies"] == {"session": "s3cret"}

        assert second["url"] == redirect_to
        assert "Authorization" not in second["kwargs"]["headers"]
        assert "X-Api-Key" not in second["kwargs"]["headers"]
        assert second["kwargs"]["headers"]["User-Agent"] == "SecuScan-Crawler/1.0"
        assert second["kwargs"]["cookies"] == {}

    @pytest.mark.asyncio
    async def test_same_origin_redirect_keeps_credentials(self):
        seed = "https://example.com/login"
        redirect_to = "https://example.com/dashboard"
        client = _FakeClient(
            {
                seed: _FakeResponse(seed, status_code=302, headers={"location": redirect_to}),
                redirect_to: _FakeResponse(redirect_to, status_code=200, headers={}),
            }
        )
        with _patch_client(client):
            with _patch_hop_validation(True):
                await crawl_target(
                    seed,
                    cookies={"session": "s3cret"},
                    extra_headers={"Authorization": "Basic dXNlcjpwYXNz"},
                )

        _, second = client.calls
        assert second["url"] == redirect_to
        assert second["kwargs"]["headers"]["Authorization"] == "Basic dXNlcjpwYXNz"
        assert second["kwargs"]["cookies"] == {"session": "s3cret"}

    @pytest.mark.asyncio
    async def test_http_to_https_same_host_is_cross_origin(self):
        seed = "http://example.com/"
        redirect_to = "https://example.com/secure"
        client = _FakeClient(
            {
                seed: _FakeResponse(seed, status_code=302, headers={"location": redirect_to}),
                redirect_to: _FakeResponse(redirect_to, status_code=200, headers={}),
            }
        )
        with _patch_client(client):
            with _patch_hop_validation(True):
                await crawl_target(
                    seed,
                    cookies={"session": "s3cret"},
                    extra_headers={"Authorization": "Basic dXNlcjpwYXNz"},
                )

        _, second = client.calls
        assert second["kwargs"]["cookies"] == {}
        assert "Authorization" not in second["kwargs"]["headers"]

    @pytest.mark.asyncio
    async def test_blocked_redirect_hop_raises_before_fetch(self):
        seed = "https://example.com/"
        redirect_to = "http://169.254.169.254/latest/meta-data/"
        client = _FakeClient(
            {seed: _FakeResponse(seed, status_code=302, headers={"location": redirect_to})}
        )
        with _patch_client(client):
            with _patch_hop_validation(False, "Destination blocked by policy"):
                with pytest.raises(ValueError, match="Redirect target blocked by network policy"):
                    await crawl_target(seed)

        fetched = [call["url"] for call in client.calls]
        assert fetched == [seed]
        assert redirect_to not in fetched

    @pytest.mark.asyncio
    async def test_redirect_chain_recorded(self):
        seed = "https://example.com/"
        mid = "https://example.com/old"
        final = "https://example.com/new"
        client = _FakeClient(
            {
                seed: _FakeResponse(seed, status_code=302, headers={"location": "/old"}),
                mid: _FakeResponse(mid, status_code=301, headers={"location": final}),
                final: _FakeResponse(final, status_code=200, headers={}),
            }
        )
        with _patch_client(client):
            with _patch_hop_validation(True):
                result = await crawl_target(seed)

        chain = result["redirect_chain"]
        assert [entry["url"] for entry in chain] == [seed, mid]
        assert [entry["status_code"] for entry in chain] == [302, 301]
        assert result["final_url"] == final
