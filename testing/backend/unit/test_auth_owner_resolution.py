"""
Unit tests for auth.py owner-resolution helpers.

Covers: resolve_owner_id, DEFAULT_OWNER_ID
"""

from backend.secuscan.auth import resolve_owner_id, DEFAULT_OWNER_ID


# ── DEFAULT_OWNER_ID ──────────────────────────────────────────────────────────


def test_default_owner_id_value():
    assert DEFAULT_OWNER_ID == "default"


# ── resolve_owner_id ──────────────────────────────────────────────────────────


def test_resolve_owner_id_with_x_user_id_header():
    """X-User-Id header with value returns prefixed owner ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "alice"})
    assert resolve_owner_id(request) == "user:alice"


def test_resolve_owner_id_trims_whitespace():
    """Leading/trailing whitespace in X-User-Id is stripped."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "  bob  "})
    assert resolve_owner_id(request) == "user:bob"


def test_resolve_owner_id_whitespace_only():
    """Whitespace-only X-User-Id falls back to DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": "   "})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_empty_header():
    """Empty X-User-Id falls back to DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({"x-user-id": ""})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_missing_header():
    """Missing X-User-Id falls back to DEFAULT_OWNER_ID."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    request = MockRequest({})
    assert resolve_owner_id(request) == DEFAULT_OWNER_ID


def test_resolve_owner_id_no_request():
    """None request falls back to DEFAULT_OWNER_ID."""
    assert resolve_owner_id(None) == DEFAULT_OWNER_ID


def test_resolve_owner_id_prefix_format():
    """Resolved owner ID always starts with 'user:' prefix."""
    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    for user_id in ["alice", "bob", "test-user-123", "UPPERCASE"]:
        request = MockRequest({"x-user-id": user_id})
        result = resolve_owner_id(request)
        assert result.startswith("user:"), f"failed for {user_id}"
        assert result == f"user:{user_id.strip()}"
