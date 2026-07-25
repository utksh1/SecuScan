"""
Edge case tests for time_utils parse_to_utc and to_utc_iso functions.

Tests non-standard inputs that the existing test suite does not cover:
- boolean values (should be rejected, not interpreted as Unix timestamps)
- whitespace-only strings
- lists and dicts
- None in to_utc_iso fallback path
"""

import pytest
from datetime import datetime, timezone

from backend.secuscan.time_utils import parse_to_utc, to_utc_iso


class TestParseToUtcBoolAndNonStringTypes:
    """Tests for non-standard type inputs to parse_to_utc."""

    def test_bool_true_returns_none(self):
        """bool True is rejected, not parsed as Unix timestamp 1."""
        assert parse_to_utc(True) is None

    def test_bool_false_returns_none(self):
        """bool False is rejected, not parsed as Unix timestamp 0."""
        assert parse_to_utc(False) is None

    def test_list_returns_none(self):
        """List input is rejected."""
        assert parse_to_utc(["2026-01-01"]) is None

    def test_dict_returns_none(self):
        """Dict input is rejected."""
        assert parse_to_utc({"key": "2026-01-01"}) is None

    def test_whitespace_only_string_returns_none(self):
        """Whitespace-only string is rejected."""
        assert parse_to_utc("   ") is None

    def test_float_still_works(self):
        """Float Unix timestamp is still accepted."""
        import time
        now_ts = time.time()
        result = parse_to_utc(now_ts)
        assert result is not None
        assert result.tzinfo == timezone.utc


class TestToUtcIsoEdgeCases:
    """Tests for edge case inputs to to_utc_iso."""

    def test_bool_true_returns_none_fallback(self):
        """bool True falls back to current UTC time (not Unix epoch + 1s)."""
        result = to_utc_iso(True)
        assert result.endswith("+00:00")
        # The fallback result should be within a few seconds of now
        from backend.secuscan.time_utils import utc_now
        fallback_dt = datetime.fromisoformat(result)
        now_dt = utc_now()
        diff = abs((fallback_dt - now_dt).total_seconds())
        assert diff < 5

    def test_bool_false_returns_none_fallback(self):
        """bool False falls back to current UTC time (not Unix epoch)."""
        result = to_utc_iso(False)
        assert result.endswith("+00:00")

    def test_list_falls_back_to_now(self):
        """List input falls back to current time."""
        result = to_utc_iso(["2026-01-01"])
        assert result.endswith("+00:00")

    def test_dict_falls_back_to_now(self):
        """Dict input falls back to current time."""
        result = to_utc_iso({"date": "2026-01-01"})
        assert result.endswith("+00:00")

    def test_whitespace_string_falls_back_to_now(self):
        """Whitespace-only string falls back to current time."""
        result = to_utc_iso("   ")
        assert result.endswith("+00:00")

    def test_valid_iso_string_preserved(self):
        """Valid ISO string is parsed and formatted correctly."""
        result = to_utc_iso("2026-01-01T12:00:00Z")
        assert result.startswith("2026-01-01T12:00:00")
        assert result.endswith("+00:00")
