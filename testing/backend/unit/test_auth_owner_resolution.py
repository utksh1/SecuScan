"""
Unit tests for auth.py owner-resolution helpers.

Covers: resolve_owner_id, DEFAULT_OWNER_ID, trusted-proxy validation (BOLA fix)
"""

from backend.secuscan.auth import resolve_owner_id, DEFAULT_OWNER_ID


class MockRequest:
    """Minimal request mock with headers and client host for proxy checks."""
    def __init__(self, headers, client_host="127.0.0.1"):
        self.headers = headers
        self.client = type("Client", (), {"host": client_host})()


# ── DEFAULT_OWNER_ID ──────────────────────────────────────────────────────────


def test_default_owner_id_value():
    assert DEFAULT_OWNER_ID == "default"


# ── resolve_owner_id ──────────────────────────────────────────────────────────


def test_resolve_owner_id_with_x_user_id_header():
    """X-User-Id header with value returns prefixed owner ID when from trusted proxy."""
    request = MockRequest({"x-user-id": "alice"}, client_host="127.0.0.1")
    assert resolve_owner_id(request) == "user:alice"


def test_resolve_owner_id_trims_whitespace():
    """Leading/trailing whitespace in X-User-Id is stripped."""
    request = MockRequest({"x-user-id": "  bob  "}, client_host="127.0.0.1")
    assert resolve_owner_id(request) == "user:bob"


def test_resolve_owner_id_whitespace_only():
    """Whitespace-only X-User-Id falls back to DEFAULT_OWNER_ID."""
    request = MockRequest({"x-user-id": "   "})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_empty_header():
    """Empty X-User-Id falls back to DEFAULT_OWNER_ID."""
    request = MockRequest({"x-user-id": ""})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_missing_header():
    """Missing X-User-Id falls back to DEFAULT_OWNER_ID."""
    request = MockRequest({})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_no_request():
    """None request falls back to DEFAULT_OWNER_ID."""
    assert resolve_owner_id(None) == DEFAULT_OWNER_ID


def test_resolve_owner_id_prefix_format():
    """Resolved owner ID always starts with 'user:' prefix when from trusted proxy."""
    for user_id in ["alice", "bob", "test-user-123", "UPPERCASE"]:
        request = MockRequest({"x-user-id": user_id}, client_host="127.0.0.1")
        result = resolve_owner_id(request)
        assert result.startswith("user:"), f"failed for {user_id}"
        assert result == f"user:{user_id.strip()}"


# ── trusted-proxy validation (Issue #2021 BOLA fix) ───────────────────────────


def test_resolve_owner_id_rejects_untrusted_proxy():
    """X-User-Id from a non-trusted IP is rejected — request scoped to default."""
    request = MockRequest({"x-user-id": "alice"}, client_host="203.0.113.50")
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_accepts_trusted_proxy():
    """X-User-Id from a trusted proxy IP is accepted."""
    request = MockRequest({"x-user-id": "alice"}, client_host="127.0.0.1")
    assert resolve_owner_id(request) == "user:alice"


def test_resolve_owner_id_accepts_ipv6_trusted_proxy():
    """X-User-Id from an IPv6 loopback trusted proxy is accepted."""
    request = MockRequest({"x-user-id": "alice"}, client_host="::1")
    assert resolve_owner_id(request) == "user:alice"


def test_resolve_owner_id_no_client_always_default():
    """Request with no client info always falls back to DEFAULT_OWNER_ID."""
    class NoClientRequest:
        def __init__(self, headers):
            self.headers = headers
            self.client = None

    request = NoClientRequest({"x-user-id": "alice"})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_attacker_impersonation_blocked():
    """REGRESSION: attacker with shared API key cannot spoof X-User-Id
    to access another workspace's data.  The header is ignored because
    the attacker's IP is not a trusted proxy."""
    # Attacker sends X-User-Id from their own machine (not a proxy)
    attacker_request = MockRequest(
        {"x-user-id": "team-alpha"}, client_host="198.51.100.23"
    )
    result = resolve_owner_id(attacker_request)
    assert result == DEFAULT_OWNER_ID, (
        "Attacker should NOT be able to impersonate team-alpha via X-User-Id"
    )

    # Legitimate request from the trusted proxy succeeds
    proxy_request = MockRequest(
        {"x-user-id": "team-alpha"}, client_host="127.0.0.1"
    )
    result = resolve_owner_id(proxy_request)
    assert result == "user:team-alpha"
