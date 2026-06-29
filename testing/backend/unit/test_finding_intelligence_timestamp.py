"""
Unit tests for finding_intelligence timestamp and ID generation helpers.

Covers:
- _parse_timestamp: converts datetime objects or ISO strings to UTC ISO format
- _stable_id: generates a deterministic short SHA-based ID from prefix and parts
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from backend.secuscan.finding_intelligence import _now_iso, _parse_timestamp, _stable_id


# ---------------------------------------------------------------------------
# _parse_timestamp
# ---------------------------------------------------------------------------

class TestParseTimestamp:
    def test_aware_datetime_returns_iso(self):
        aware = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _parse_timestamp(aware)
        assert result.startswith("2024-06-01")

    def test_naive_datetime_returns_iso(self):
        naive = datetime(2024, 6, 1, 12, 0, 0)
        result = _parse_timestamp(naive)
        assert result.startswith("2024-06-01")

    def test_iso_string_with_z_suffix(self):
        result = _parse_timestamp("2024-06-01T12:00:00Z")
        assert result.startswith("2024-06-01")

    def test_iso_string_without_z_suffix(self):
        result = _parse_timestamp("2024-06-01T12:00:00+00:00")
        assert result.startswith("2024-06-01")

    def test_invalid_string_returns_iso_now(self):
        before = datetime.now(timezone.utc)
        result = _parse_timestamp("not-a-date")
        after = datetime.now(timezone.utc)
        # Should return an ISO string near current time
        assert result.endswith("+00:00")
        parsed = datetime.fromisoformat(result)
        assert before <= parsed <= after

    def test_empty_string_returns_iso_now(self):
        result = _parse_timestamp("")
        # Returns an ISO timestamp near now
        assert "+00:00" in result or "Z" in result
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_none_returns_iso_now(self):
        before = datetime.now(timezone.utc)
        result = _parse_timestamp(None)
        after = datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert before <= parsed <= after

    def test_microseconds_preserved(self):
        result = _parse_timestamp("2024-06-01T12:00:00.123456Z")
        assert ".123456" in result

    def test_non_utc_timezone_converted_to_utc(self):
        # +05:30 offset should be converted to UTC (+00:00)
        result = _parse_timestamp("2024-06-01T12:00:00+05:30")
        # 12:00 +05:30 = 06:30 UTC
        assert result.startswith("2024-06-01")
        # Verify the offset is UTC
        assert result.endswith("+00:00")


# ---------------------------------------------------------------------------
# _stable_id
# ---------------------------------------------------------------------------

class TestStableId:
    def test_prefix_in_output(self):
        sig = _stable_id("asset", "example.com")
        assert sig.startswith("asset:")

    def test_same_inputs_produce_same_output(self):
        sig1 = _stable_id("asset", "example.com", "443")
        sig2 = _stable_id("asset", "example.com", "443")
        assert sig1 == sig2

    def test_different_inputs_produce_different_output(self):
        sig1 = _stable_id("asset", "example.com")
        sig2 = _stable_id("asset", "different.com")
        assert sig1 != sig2

    def test_different_prefixes_produce_different_output(self):
        sig1 = _stable_id("asset", "example.com")
        sig2 = _stable_id("group", "example.com")
        assert sig1 != sig2

    def test_none_parts_handled(self):
        sig = _stable_id("asset", None, "example.com")
        assert sig.startswith("asset:")

    def test_empty_parts_handled(self):
        sig = _stable_id("asset", "", "example.com")
        assert sig.startswith("asset:")

    def test_whitespace_parts_normalized(self):
        sig1 = _stable_id("asset", "  example.com  ")
        sig2 = _stable_id("asset", "example.com")
        assert sig1 == sig2

    def test_case_normalized(self):
        sig1 = _stable_id("asset", "EXAMPLE.COM")
        sig2 = _stable_id("asset", "example.com")
        assert sig1 == sig2

    def test_id_has_correct_length(self):
        sig = _stable_id("asset", "example.com")
        # format: prefix:SHA (prefix + : + 16-char hex digest)
        assert len(sig) == len("asset:") + 16

    def test_many_parts(self):
        sig = _stable_id("finding", "a", "b", "c", "d", "e")
        assert sig.startswith("finding:")


# ---------------------------------------------------------------------------
# _now_iso
# ---------------------------------------------------------------------------

class TestNowIso:
    def test_returns_string(self):
        """_now_iso returns a string."""
        result = _now_iso()
        assert isinstance(result, str)

    def test_returns_valid_iso8601_format(self):
        """_now_iso returns a valid ISO 8601 formatted datetime string."""
        result = _now_iso()
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)

    def test_returns_utc_timezone(self):
        """_now_iso returns a UTC timezone-aware datetime string."""
        result = _now_iso()
        assert result.endswith("+00:00") or result.endswith("Z")

    def test_result_is_reasonable_current_time(self):
        """_now_iso returns a time within a few seconds of now."""
        before = datetime.now(timezone.utc)
        result = _now_iso()
        after = datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
        assert before <= parsed <= after
