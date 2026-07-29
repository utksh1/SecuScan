"""
Unit tests for parse_to_utc edge cases in time_utils.

Covers: invalid strings, ambiguous formats, timezone edge cases, non-UTC offsets,
and inputs that previously caused crashes or wrong results.
"""

import pytest
from datetime import datetime, timezone
from backend.secuscan.time_utils import parse_to_utc


class TestParseToUtcEdgeCases:
    """Edge case tests for parse_to_utc."""

    # ── None / empty / non-string input ───────────────────────────────────────

    def test_none_returns_none(self):
        """None is a no-op that returns None."""
        assert parse_to_utc(None) is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert parse_to_utc("") is None

    def test_whitespace_only_returns_none(self):
        """Whitespace-only string returns None."""
        assert parse_to_utc("   ") is None

    # ── Unparseable strings → None ───────────────────────────────────────────

    def test_broken_iso_format_returns_none(self):
        """Garbage string returns None."""
        assert parse_to_utc("not-a-date") is None

    def test_incomplete_iso_returns_none(self):
        """Incomplete ISO fragment returns None."""
        assert parse_to_utc("2024-01-01T") is None

    def test_pure_time_string_returns_none(self):
        """Time-only string is not a full date."""
        assert parse_to_utc("12:34:56") is None

    def test_us_date_format_returns_none(self):
        """US MM/DD/YYYY is not ISO – returns None."""
        assert parse_to_utc("01/15/2024") is None

    def test_eu_date_format_returns_none(self):
        """EU DD/MM/YYYY is not ISO – returns None."""
        assert parse_to_utc("15/01/2024") is None

    def test_slash_datetime_returns_none(self):
        """Slash-separated datetime is not ISO."""
        assert parse_to_utc("2024/01/15 12:00:00") is None

    def test_dot_separated_returns_none(self):
        """Dot-separated datetime is not ISO."""
        assert parse_to_utc("2024.01.15T12:00:00") is None

    # ── Date-only is NOT parseable ──────────────────────────────────────────

    def test_dash_date_only_parsed_as_midnight_utc(self):
        """YYYY-MM-DD (date-only) is parsed as midnight UTC."""
        result = parse_to_utc("2024-01-15")
        assert result == datetime(2024, 1, 15, 0, 0, 0, tzinfo=timezone.utc)

    # ── Unix timestamp (int / float) ─────────────────────────────────────────

    def test_unix_timestamp_int(self):
        """Integer is interpreted as Unix epoch seconds."""
        result = parse_to_utc(1704067200)
        assert result == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_unix_timestamp_float(self):
        """Float is interpreted as Unix epoch with sub-second precision."""
        result = parse_to_utc(1704067200.123)
        assert result.microsecond == 123000

    # ── "now" special keyword ─────────────────────────────────────────────────

    def test_now_returns_current_utc(self):
        """The literal 'now' returns a UTC-aware current time."""
        import time
        before = datetime.now(timezone.utc)
        time.sleep(0.01)
        result = parse_to_utc("now")
        time.sleep(0.01)
        after = datetime.now(timezone.utc)
        assert before <= result <= after
        assert result.tzinfo == timezone.utc

    # ── Space separator (SQLite convention) ──────────────────────────────────

    def test_space_separator_converted_to_T(self):
        """Space-separated ISO (SQLite format) is handled."""
        result = parse_to_utc("2024-06-15 14:30:00")
        assert result == datetime(2024, 6, 15, 14, 30, 0, tzinfo=timezone.utc)

    # ── Z suffix ─────────────────────────────────────────────────────────────

    def test_z_suffix_handled(self):
        """Z suffix is accepted and converted to +00:00."""
        result = parse_to_utc("2024-01-01T00:00:00Z")
        assert result == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    # ── Sub-second precision ──────────────────────────────────────────────────

    def test_microseconds_preserved(self):
        """Sub-second precision is preserved."""
        result = parse_to_utc("2024-06-15T14:30:00.123456")
        assert result == datetime(2024, 6, 15, 14, 30, 0, 123456, tzinfo=timezone.utc)

    def test_subseconds_rounded_to_microseconds(self):
        """Nano-second precision is truncated to microseconds."""
        result = parse_to_utc("2024-06-15T14:30:00.123456789")
        assert result.microsecond == 123456

    # ── UTC offset handling ──────────────────────────────────────────────────

    def test_positive_offset_converted_to_utc(self):
        """Positive UTC+N offset is converted to UTC."""
        result = parse_to_utc("2024-01-01T03:00:00+03:00")
        assert result == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_negative_offset_converted_to_utc(self):
        """Negative UTC-N offset is converted to UTC."""
        result = parse_to_utc("2024-01-01T03:00:00-05:00")
        assert result == datetime(2024, 1, 1, 8, 0, 0, tzinfo=timezone.utc)

    def test_offset_without_colon(self):
        """Offset without colon separator: +0300."""
        result = parse_to_utc("2024-01-01T03:00:00+0300")
        assert result == datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_india_offset(self):
        """India +05:30 is correctly converted."""
        result = parse_to_utc("2024-01-01T09:30:00+05:30")
        assert result == datetime(2024, 1, 1, 4, 0, 0, tzinfo=timezone.utc)

    def test_nz_negative_fractional_offset(self):
        """NZ -08:30 (Chatham Islands) is correctly converted."""
        result = parse_to_utc("2024-01-01T12:00:00-08:30")
        assert result == datetime(2024, 1, 1, 20, 30, 0, tzinfo=timezone.utc)

    # ── Leap second ─────────────────────────────────────────────────────────

    def test_leap_second_returns_none(self):
        """Leap second (60s) is not supported – returns None."""
        assert parse_to_utc("2024-01-01T00:00:60Z") is None

    # ── Year boundary ────────────────────────────────────────────────────────

    def test_year_boundary_crossing(self):
        """Year rollover at UTC midnight is preserved."""
        result = parse_to_utc("2023-12-31T23:59:59Z")
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 31
        assert result.hour == 23

    # ── Naive datetime (no tzinfo) ──────────────────────────────────────────

    def test_naive_utc_interpreted_as_utc(self):
        """Naive datetime is treated as UTC (SQLite storage semantics)."""
        result = parse_to_utc("2024-01-01T12:00:00")
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # ── Already-aware datetime ──────────────────────────────────────────────

    def test_aware_utc_returns_utc_equivalent(self):
        """Already-UTC-aware datetime returns UTC equivalent."""
        aware = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = parse_to_utc(aware)
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_non_utc_aware_converted_to_utc(self):
        """Non-UTC aware datetime is converted to UTC."""
        import zoneinfo
        est = zoneinfo.ZoneInfo("America/New_York")
        aware = datetime(2024, 1, 1, 7, 0, 0, tzinfo=est)  # 12:00 UTC
        result = parse_to_utc(aware)
        assert result == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    # ── Epoch boundaries ────────────────────────────────────────────────────

    def test_epoch_start(self):
        """Unix epoch start is correctly parsed."""
        result = parse_to_utc("1970-01-01T00:00:00Z")
        assert result == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
