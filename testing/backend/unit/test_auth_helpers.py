"""
Unit tests for backend.secuscan.auth pure helpers.

Covers:
- resolve_owner_id returns DEFAULT_OWNER_ID when request is None
- resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id header is absent
- resolve_owner_id returns user:<id> when X-User-Id header is present and from trusted proxy
- resolve_owner_id strips whitespace from user ID
- resolve_owner_id rejects X-User-Id from untrusted sources (BOLA fix)
- get_api_key returns the current API key or None when not initialised
"""

from unittest.mock import MagicMock

from backend.secuscan import auth


def _mock_request(headers, client_host="127.0.0.1"):
    """Create a mock request with headers and a client host for proxy checks."""
    req = MagicMock()
    req.headers = headers
    req.client = MagicMock()
    req.client.host = client_host
    return req


class TestResolveOwnerId:
    def test_returns_default_when_request_is_none(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when request is None."""
        result = auth.resolve_owner_id(None)
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_header_absent(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id is absent."""
        result = auth.resolve_owner_id(_mock_request({}))
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_header_empty(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id is empty."""
        result = auth.resolve_owner_id(_mock_request({"x-user-id": ""}))
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_user_prefix_when_header_present_and_trusted_proxy(self):
        """resolve_owner_id returns 'user:<id>' when X-User-Id is set and from trusted proxy."""
        result = auth.resolve_owner_id(
            _mock_request({"x-user-id": "alice"}, client_host="127.0.0.1")
        )
        assert result == "user:alice"

    def test_strips_whitespace_from_user_id(self):
        """resolve_owner_id strips leading/trailing whitespace from user ID."""
        result = auth.resolve_owner_id(
            _mock_request({"x-user-id": "  bob  "}, client_host="127.0.0.1")
        )
        assert result == "user:bob"

    def test_returns_default_when_header_from_untrusted_source(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID for X-User-Id from untrusted IP."""
        result = auth.resolve_owner_id(
            _mock_request({"x-user-id": "alice"}, client_host="203.0.113.50")
        )
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_no_client_info(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when request has no client info."""
        req = MagicMock()
        req.headers = {"x-user-id": "alice"}
        req.client = None
        result = auth.resolve_owner_id(req)
        assert result == auth.DEFAULT_OWNER_ID


class TestGetApiKey:
    def test_returns_none_when_not_initialised(self):
        """get_api_key returns None before init_api_key is called."""
        original = auth._api_key
        auth._api_key = None
        try:
            result = auth.get_api_key()
            assert result is None
        finally:
            auth._api_key = original
