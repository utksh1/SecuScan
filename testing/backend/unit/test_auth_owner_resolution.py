"""
Unit tests for auth.py owner-resolution helpers.

Covers: resolve_owner_id, DEFAULT_OWNER_ID

Security model: resolve_owner_id ignores the X-User-Id header and always
returns DEFAULT_OWNER_ID to prevent header-spoofing BOLA attacks.
"""

from backend.secuscan.auth import resolve_owner_id, DEFAULT_OWNER_ID


# ── DEFAULT_OWNER_ID ──────────────────────────────────────────────────────────


def test_default_owner_id_value():
    assert DEFAULT_OWNER_ID == "default"


# ── resolve_owner_id ──────────────────────────────────────────────────────────


def test_resolve_owner_id_with_x_user_id_header():
    """X-User-Id header is IGNORED — owner always resolves to default."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "alice"})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_trims_whitespace():
    """Whitespace in X-User-Id does not change the resolved owner."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "  bob  "})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_whitespace_only():
    """Whitespace-only X-User-Id still returns DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "   "})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_empty_header():
    """Empty X-User-Id returns DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": ""})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_missing_header():
    """Missing X-User-Id returns DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_no_request():
    """None request falls back to DEFAULT_OWNER_ID."""
    assert resolve_owner_id(None) == DEFAULT_OWNER_ID


def test_resolve_owner_id_header_spoofing_blocked():
    """Spoofing X-User-Id to impersonate another owner is blocked."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    for user_id in ["alice", "bob", "test-user-123", "UPPERCASE", "admin"]:
        request = MockRequest({"x-user-id": user_id})
        result = resolve_owner_id(request)
        assert result == DEFAULT_OWNER_ID, (
            f"X-User-Id header '{user_id}' was trusted — spoofing is not blocked"
        )
        assert not result.startswith("user:"), (
            f"Header spoofing produced owner '{result}' instead of default"
        )
