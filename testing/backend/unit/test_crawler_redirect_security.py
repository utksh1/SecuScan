"""Unit tests for crawler redirect hardening.

Covers the two halves of the redirect SSRF / credential-exfiltration fix in
``backend/secuscan/crawler.py``:

1. Redirect hops are re-validated against the network policy before they are
   fetched, so a hostile seed cannot pivot the crawler into cloud-metadata,
   loopback, or private ranges (SSRF).
2. Credentials (``extra_headers`` / ``cookies``) are only sent to the seed
   origin and are stripped on any cross-origin redirect, so vault credentials
   cannot be leaked to an attacker-controlled host.

Related issue: https://github.com/utksh1/SecuScan/issues/2369
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

import httpx
import pytest

from backend.secuscan.crawler import (
    _is_same_origin,
    _validate_redirect_target,
    crawl_target,
)


class _FakePolicyEngine:
    """Minimal stand-in for NetworkPolicyEngine.

    Denies the cloud-metadata / link-local range (169.254.0.0/16) like the
    real mandatory denylist, allows everything else, and records calls so the
    tests can assert the crawler passes the redirect host for validation.
    """

    def __init__(self, *, raise_on_check: bool = False):
        self.calls = []
        self.raise_on_check = raise_on_check

    def check_access(self, dest_ip, dest_port=0, plugin_id="unknown", task_id="unknown", dest_hostname=None):
        self.calls.append({"dest_ip": dest_ip, "dest_hostname": dest_hostname})
        if self.raise_on_check:
            raise RuntimeError("policy engine exploded")
        try:
            import ipaddress
            ip = ipaddress.ip_address(dest_ip)
            if ip in ipaddress.ip_network("169.254.0.0/16"):
                return False, "Blocked by mandatory denylist (matched: 169.254.0.0/16)", None
        except ValueError:
            pass
        return True, "Allowed", None


def _make_response(status_code, url, *, headers=None, body=b"<html></html>"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.headers = dict(headers or {})
    resp.history = []

    async def _aiter_bytes():
        yield body

    resp.aiter_bytes = _aiter_bytes
    resp.request = httpx.Request("GET", url)
    return resp


def _stream_context(response):
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def _make_client(*responses):
    """Build a mocked AsyncClient that yields one streamed response per call."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.stream.side_effect = [_stream_context(resp) for resp in responses]
    return client


# ---------------------------------------------------------------------------
# _is_same_origin
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "origin,other,expected",
    [
        ("https://example.com/a", "https://example.com/b", True),
        ("http://example.com:80/x", "http://example.com/y", True),
        ("https://example.com:443/x", "https://example.com/y", True),
        ("https://example.com/x", "https://other.com/y", False),
        ("http://example.com/x", "https://example.com/y", False),
        ("https://example.com:8080/x", "https://example.com/y", False),
        ("https://example.com/x", "https://EXAMPLE.com/y", True),
    ],
)
def test_is_same_origin(origin, other, expected):
    assert _is_same_origin(urlparse(origin), urlparse(other)) is expected


def test_is_same_origin_malformed_port_is_cross_origin():
    # A malformed port on the redirect target must never be treated as the
    # same origin, so credentials are dropped.
    assert _is_same_origin(
        urlparse("https://example.com/"), urlparse("https://example.com:bad/")
    ) is False


# ---------------------------------------------------------------------------
# _validate_redirect_target
# ---------------------------------------------------------------------------


def test_validate_redirect_target_rejects_unsupported_scheme():
    ok, reason = _validate_redirect_target("ftp://example.com/x")
    assert ok is False
    assert "unsupported scheme" in reason


def test_validate_redirect_target_rejects_missing_hostname():
    ok, reason = _validate_redirect_target("http://")
    assert ok is False
    assert "no hostname" in reason


def test_validate_redirect_target_consults_policy_engine():
    engine = _FakePolicyEngine()
    with patch("backend.secuscan.network_policy.get_policy_engine", return_value=engine):
        ok, reason = _validate_redirect_target("http://169.254.169.254/latest/meta-data/")
    assert ok is False
    assert "denylist" in reason
    assert engine.calls[-1]["dest_ip"] == "169.254.169.254"
    assert engine.calls[-1]["dest_hostname"] == "169.254.169.254"


def test_validate_redirect_target_fails_closed_on_engine_error():
    engine = _FakePolicyEngine(raise_on_check=True)
    with patch("backend.secuscan.network_policy.get_policy_engine", return_value=engine):
        ok, reason = _validate_redirect_target("http://169.254.169.254/latest/meta-data/")
    assert ok is False
    assert "could not be validated" in reason


# ---------------------------------------------------------------------------
# crawl_target redirect behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crawl_target_blocks_redirect_to_cloud_metadata():
    """A redirect into the metadata/link-local range must abort the crawl.

    The redirect destination is never fetched (stream is called once for the
    seed), proving the SSRF pivot is closed rather than merely logged.
    """
    seed = "http://example.com/"
    redirect_url = "http://169.254.169.254/latest/meta-data/"
    client = _make_client(
        _make_response(302, seed, headers={"location": redirect_url}),
        _make_response(200, redirect_url, body=b"iam metadata"),
    )
    engine = _FakePolicyEngine()

    with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=client):
        with patch("backend.secuscan.crawler.settings") as mock_settings:
            mock_settings.verify_ssl = True
            mock_settings.enforce_network_policy = True
            with patch("backend.secuscan.network_policy.get_policy_engine", return_value=engine):
                with pytest.raises(ValueError, match="rejected by network policy"):
                    await crawl_target(seed, extra_headers={"Authorization": "Basic dXNlcjpwYXNz"})

    # The metadata endpoint must never have been requested.
    assert client.stream.call_count == 1
    assert engine.calls[-1]["dest_ip"] == "169.254.169.254"


@pytest.mark.asyncio
async def test_crawl_target_strips_credentials_on_cross_origin_redirect():
    """Cross-origin redirects must not inherit the seed's Authorization or cookies."""
    seed = "https://example.com/"
    attacker = "https://attacker.example/collect"
    client = _make_client(
        _make_response(302, seed, headers={"location": attacker}),
        _make_response(200, attacker, body=b"<html>pwned</html>"),
    )
    extra_headers = {"Authorization": "Basic dXNlcjpwYXNz", "X-Custom": "keep"}
    cookies = {"session": "secret"}

    with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=client):
        with patch("backend.secuscan.crawler.settings") as mock_settings:
            mock_settings.verify_ssl = True
            mock_settings.enforce_network_policy = False
            result = await crawl_target(
                seed, extra_headers=extra_headers, cookies=cookies
            )

    calls = client.stream.call_args_list
    assert len(calls) == 2

    first_headers = calls[0].kwargs["headers"]
    assert first_headers["Authorization"] == "Basic dXNlcjpwYXNz"
    assert first_headers["X-Custom"] == "keep"
    assert calls[0].kwargs["cookies"] == {"session": "secret"}

    second_headers = calls[1].kwargs["headers"]
    assert "Authorization" not in second_headers
    assert "X-Custom" not in second_headers
    assert calls[1].kwargs["cookies"] == {}

    assert result["final_url"] == attacker
    assert result["redirect_chain"] == [
        {"url": seed, "status_code": 302, "location": attacker}
    ]


@pytest.mark.asyncio
async def test_crawl_target_keeps_credentials_on_same_origin_redirect():
    """Same-origin redirects legitimately keep the configured credentials."""
    seed = "https://example.com/"
    login = "https://example.com/login"
    client = _make_client(
        _make_response(302, seed, headers={"location": login}),
        _make_response(200, login, body=b"<html>login</html>"),
    )
    extra_headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    cookies = {"session": "secret"}

    with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=client):
        with patch("backend.secuscan.crawler.settings") as mock_settings:
            mock_settings.verify_ssl = True
            mock_settings.enforce_network_policy = False
            result = await crawl_target(
                seed, extra_headers=extra_headers, cookies=cookies
            )

    calls = client.stream.call_args_list
    assert len(calls) == 2
    assert calls[1].kwargs["headers"]["Authorization"] == "Basic dXNlcjpwYXNz"
    assert calls[1].kwargs["cookies"] == {"session": "secret"}
    assert result["final_url"] == login


@pytest.mark.asyncio
async def test_crawl_target_enforces_manual_redirect_limit():
    """The manual redirect loop must still cap the chain at max_redirects."""
    client = _make_client(
        _make_response(302, "http://example.com/", headers={"location": "http://example.com/b"}),
        _make_response(302, "http://example.com/b", headers={"location": "http://example.com/c"}),
        _make_response(302, "http://example.com/c", headers={"location": "http://example.com/d"}),
    )

    with patch("backend.secuscan.crawler.httpx.AsyncClient", return_value=client):
        with patch("backend.secuscan.crawler.settings") as mock_settings:
            mock_settings.verify_ssl = True
            mock_settings.enforce_network_policy = False
            with pytest.raises(httpx.TooManyRedirects):
                await crawl_target("http://example.com/", max_redirects=2)

    assert client.stream.call_count == 3
