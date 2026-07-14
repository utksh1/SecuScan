"""
Unit tests for auth.py owner-resolution helpers.

Covers: resolve_owner_id, DEFAULT_OWNER_ID, trusted_owner_ids whitelist
"""

from unittest.mock import patch

from backend.secuscan.auth import resolve_owner_id, DEFAULT_OWNER_ID


# ── DEFAULT_OWNER_ID ──────────────────────────────────────────────────────────


def test_default_owner_id_value():
    assert DEFAULT_OWNER_ID == "default"


# ── resolve_owner_id ──────────────────────────────────────────────────────────


class MockRequest:
    def __init__(self, headers):
        self.headers = headers


def test_resolve_owner_id_with_x_user_id_header():
    """X-User-Id header with value returns prefixed owner ID when trusted."""
    request = MockRequest({"x-user-id": "alice"})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = ["alice", "bob"]
        assert resolve_owner_id(request) == "user:alice"


def test_resolve_owner_id_trims_whitespace():
    """Leading/trailing whitespace in X-User-Id is stripped."""
    request = MockRequest({"x-user-id": "  bob  "})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = ["bob"]
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
    """Resolved owner ID always starts with 'user:' prefix when trusted."""
    for user_id in ["alice", "bob", "test-user-123", "UPPERCASE"]:
        request = MockRequest({"x-user-id": user_id})
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.trusted_owner_ids = [user_id]
            result = resolve_owner_id(request)
            assert result.startswith("user:"), f"failed for {user_id}"
            assert result == f"user:{user_id.strip()}"


# ── trusted_owner_ids whitelist (Issue #2021 BOLA fix) ────────────────────────


def test_resolve_owner_id_rejects_untrusted_user():
    """Untrusted X-User-Id falls back to DEFAULT_OWNER_ID."""
    request = MockRequest({"x-user-id": "attacker"})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = ["alice", "bob"]
        assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_empty_whitelist_ignores_header():
    """Empty trusted_owner_ids means X-User-Id is always ignored."""
    request = MockRequest({"x-user-id": "alice"})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = []
        assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_no_whitelist_config_ignores_header():
    """Missing trusted_owner_ids config means X-User-Id is always ignored."""
    request = MockRequest({"x-user-id": "alice"})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = None
        assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_trusted_user_accepted():
    """Trusted X-User-Id is accepted and returned with user: prefix."""
    request = MockRequest({"x-user-id": "team-alpha"})
    with patch("backend.secuscan.config.settings") as mock_settings:
        mock_settings.trusted_owner_ids = ["team-alpha", "team-beta"]
        assert resolve_owner_id(request) == "user:team-alpha"
