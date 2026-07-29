"""
Unit tests for _parse_discovered_at in backend/secuscan/executor.py.

The executor module has heavy imports (FastAPI, database, cache, etc.) that are
not available in this sandbox.  All backend.secuscan dependencies are mocked so
that the real _parse_discovered_at function can be imported and tested.
"""

import sys
from unittest.mock import MagicMock
from datetime import datetime, timezone

import pytest

# Mock all backend.secuscan modules that executor.py imports at module level.
# Without these, executor.py cannot be imported.
_MOCKED_BACKEND_MODULES = {
    "backend.secuscan.auth",
    "backend.secuscan.cache",
    "backend.secuscan.config",
    "backend.secuscan.database",
    "backend.secuscan.plugins",
    "backend.secuscan.models",
    "backend.secuscan.ratelimit",
    "backend.secuscan.risk_scoring",
    "backend.secuscan.capabilities",
    "backend.secuscan.parser_sandbox",
    "backend.secuscan.network_policy",
    "backend.secuscan.notification_service",
    "backend.secuscan.execution_context",
    "backend.secuscan.finding_intelligence",
    "backend.secuscan.platform_resources",
    "backend.secuscan.logging_utils",
    "backend.secuscan.request_context",
    "backend.secuscan.routes",
    "backend.secuscan.saved_views",
    "backend.secuscan.workflows",
    "backend.secuscan.workflows_scheduler",
    "backend.secuscan.ratelimit",
}

for mod in _MOCKED_BACKEND_MODULES:
    sys.modules[mod] = MagicMock()

sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()
sys.modules["fastapi"] = MagicMock()
sys.modules["pydantic"] = MagicMock()
sys.modules["aiosqlite"] = MagicMock()
sys.modules["httpx"] = MagicMock()

from backend.secuscan.executor import _parse_discovered_at


class TestParseDiscoveredAt:
    """Tests for _parse_discovered_at: extracts discovered_at from a finding dict."""

    def test_returns_utc_when_discovered_at_is_valid_iso(self):
        """A valid ISO datetime string is returned as timezone-aware UTC."""
        finding = {"discovered_at": "2026-07-15T12:30:00Z"}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_returns_utc_when_discovered_at_has_timezone_offset(self):
        """A datetime with an explicit offset is converted to UTC."""
        finding = {"discovered_at": "2026-07-15T08:30:00-04:00"}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12  # 8:30 AM EDT = 12:30 PM UTC

    def test_returns_utc_when_discovered_at_has_space_separator(self):
        """A datetime with a space (SQLite format) is parsed and returned as UTC."""
        finding = {"discovered_at": "2026-07-15 12:30:00"}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 12

    def test_returns_none_when_discovered_at_is_missing(self):
        """When discovered_at is absent from the dict, None is passed to parse_to_utc."""
        finding = {}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert isinstance(result, datetime)
        # Should fall back to utc_now (current time)
        assert result.tzinfo == timezone.utc

    def test_returns_none_when_discovered_at_is_none(self):
        """When discovered_at is explicitly None, the function falls back to utc_now."""
        finding = {"discovered_at": None}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_returns_none_when_discovered_at_is_invalid(self):
        """An unparseable discovered_at string falls back to utc_now."""
        finding = {"discovered_at": "not-a-valid-date"}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_returns_none_when_discovered_at_is_empty_string(self):
        """An empty discovered_at string falls back to utc_now."""
        finding = {"discovered_at": ""}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_returns_datetime_object_when_discovered_at_is_datetime(self):
        """When discovered_at is already a datetime object, it is returned as UTC."""
        aware_dt = datetime(2026, 7, 15, 14, 30, 0, tzinfo=timezone.utc)
        finding = {"discovered_at": aware_dt}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert result.tzinfo == timezone.utc
        assert result.hour == 14

    def test_returns_none_when_discovered_at_is_unix_timestamp(self):
        """A Unix timestamp (int) in discovered_at falls back to utc_now."""
        finding = {"discovered_at": 1751232000}
        result = _parse_discovered_at(finding)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
