"""
Unit tests for backend.secuscan.auth pure helpers.

Covers:
- resolve_owner_id returns DEFAULT_OWNER_ID when request is None
- resolve_owner_id returns DEFAULT_OWNER_ID when X-User-Id header is absent
- resolve_owner_id returns user:<id> when X-User-Id header is present and trusted
- resolve_owner_id strips whitespace from user ID
- resolve_owner_id rejects untrusted X-User-Id values (BOLA fix)
- get_api_key returns the current API key or None when not initialised
"""

from unittest.mock import MagicMock, patch

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

    def test_returns_user_prefix_when_header_present_and_trusted(self):
        """resolve_owner_id returns 'user:<id>' when X-User-Id is set and trusted."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "alice"}
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.trusted_owner_ids = ["alice", "bob"]
            result = auth.resolve_owner_id(mock_request)
            assert result == "user:alice"

    def test_strips_whitespace_from_user_id(self):
        """resolve_owner_id strips leading/trailing whitespace from user ID."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "  bob  "}
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.trusted_owner_ids = ["bob"]
            result = auth.resolve_owner_id(mock_request)
            assert result == "user:bob"

    def test_returns_default_when_user_not_in_trusted_list(self):
        """resolve_owner_id returns DEFAULT_OWNER_ID for untrusted X-User-Id."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "attacker"}
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.trusted_owner_ids = ["alice", "bob"]
            result = auth.resolve_owner_id(mock_request)
            assert result == auth.DEFAULT_OWNER_ID

    def test_returns_default_when_trusted_list_is_empty(self):
        """resolve_owner_id ignores X-User-Id when trusted_owner_ids is empty."""
        mock_request = MagicMock()
        mock_request.headers = {"x-user-id": "alice"}
        with patch("backend.secuscan.config.settings") as mock_settings:
            mock_settings.trusted_owner_ids = []
            result = auth.resolve_owner_id(mock_request)
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
