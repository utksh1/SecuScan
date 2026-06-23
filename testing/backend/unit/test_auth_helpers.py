"""
Unit tests for backend.secuscan.auth pure helpers.

Covers:
- resolve_owner_id returns DEFAULT_OWNER_ID when request is None
- resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id header is absent
- resolve_owner_id returns user:<id> when X-User-Id header is present
- resolve_owner_id strips whitespace from user ID
- get_api_key returns the current API key or None when not initialised
"""

from unittest.mock import MagicMock

from backend.secuscan import auth


class TestResolveOwnerId:
    def test_returns_default_when_request_is_none(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when request is None."""
        result = auth.resolve_owner_id(None)
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_header_absent(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id is absent."""
        mock_request = MagicMock()
        mock_request.headers = {}
        result = auth.resolve_owner_id(mock_request)
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_header_empty(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id is empty."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": ""}
        result = auth.resolve_owner_id(mock_request)
        assert result == auth.DEFAULT_OWNER_ID

    def test_returns_user_prefix_when_header_present(self):
        """resolve_owner_id returns 'user:<id>' when X-User-Id is set."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "alice"}
        result = auth.resolve_owner_id(mock_request)
        assert result == "user:alice"

    def test_strips_whitespace_from_user_id(self):
        """resolve_owner_id strips leading/trailing whitespace from user ID."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "  bob  "}
        result = auth.resolve_owner_id(mock_request)
        assert result == "user:bob"


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
