"""
Unit tests for _parse_discovered_at datetime parsing edge cases in
backend/secuscan/risk_scoring.py.

The _parse_discovered_at function handles discovered_at field parsing
for risk scoring. While test_risk_scoring.py covers the basic cases,
this file covers additional edge cases not yet tested.
Note: _parse_discovered_at is defined in backend.secuscan.executor but
re-exported by risk_scoring.py so it can be imported from either module.
"""

import pytest
from datetime import datetime, timezone, timedelta


def _parse_discovered_at(finding: dict) -> datetime | None:
    """Import and call the helper being tested."""
    # Import from executor where the function is defined
    from backend.secuscan.executor import _parse_discovered_at as _fn
    return _fn(finding)


class TestParseDiscoveredAtBasicEdgeCases:
    """Basic inputs for _parse_discovered_at."""

    def test_iso_string_with_z_suffix(self):
        """ISO string with Z suffix is parsed correctly."""
        result = _parse_discovered_at({"discovered_at": "2026-01-15T10:30:00Z"})
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_iso_string_without_z_suffix(self):
        """ISO string without Z suffix (naive datetime) is parsed."""
        result = _parse_discovered_at({"discovered_at": "2026-06-20T12:00:00"})
        assert result is not None
        assert result.year == 2026
        assert result.month == 6
        assert result.day == 20

    def test_datetime_object_passed_through(self):
        """A datetime object is returned unchanged."""
        dt = datetime(2026, 3, 10, 14, 30, 0, tzinfo=timezone.utc)
        result = _parse_discovered_at({"discovered_at": dt})
        assert result is dt

    def test_none_uses_now(self):
        """None discovered_at falls back to current time."""
        before = datetime.now(timezone.utc)
        result = _parse_discovered_at({"discovered_at": None})
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    def test_missing_key_uses_now(self):
        """A finding dict without discovered_at key falls back to now."""
        before = datetime.now(timezone.utc)
        result = _parse_discovered_at({})
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    def test_empty_string_uses_now(self):
        """Empty string falls back to now."""
        before = datetime.now(timezone.utc)
        result = _parse_discovered_at({"discovered_at": ""})
        after = datetime.now(timezone.utc)
        assert before <= result <= after

    def test_invalid_string_uses_now(self):
        """An invalid date string falls back to now."""
        before = datetime.now(timezone.utc)
        result = _parse_discovered_at({"discovered_at": "not-a-date"})
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestParseDiscoveredAtTimezones:
    """Timezone-aware datetime parsing."""

    def test_iso_string_with_positive_offset(self):
        """ISO string with +HH:MM offset is parsed correctly."""
        result = _parse_discovered_at({"discovered_at": "2026-07-01T12:00:00+05:30"})
        assert result is not None
        assert result.year == 2026

    def test_iso_string_with_negative_offset(self):
        """ISO string with -HH:MM offset is parsed correctly."""
        result = _parse_discovered_at({"discovered_at": "2026-07-01T12:00:00-08:00"})
        assert result is not None
        assert result.year == 2026

    def test_naive_datetime_not_utc(self):
        """A naive (non-tz-aware) datetime is handled without error."""
        naive_dt = datetime.now().replace(tzinfo=None)
        result = _parse_discovered_at({"discovered_at": naive_dt})
        assert result is not None


class TestParseDiscoveredAtEdgeValues:
    """Edge values for discovered_at."""

    def test_very_old_date(self):
        """A very old discovered_at date is parsed without error."""
        result = _parse_discovered_at({"discovered_at": "1990-01-01T00:00:00Z"})
        assert result is not None
        assert result.year == 1990

    def test_future_date(self):
        """A future discovered_at date is parsed without error."""
        future = datetime.now(timezone.utc) + timedelta(days=365)
        future_str = future.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = _parse_discovered_at({"discovered_at": future_str})
        assert result is not None
        assert result > datetime.now(timezone.utc)

    def test_unicode_string_falls_back_to_now(self):
        """A Unicode non-date string falls back to now."""
        before = datetime.now(timezone.utc)
        result = _parse_discovered_at({"discovered_at": "\u0000\ufeff"})
        after = datetime.now(timezone.utc)
        assert before <= result <= after
