"""
Unit tests for edge cases in parse_to_utc in backend/secuscan/time_utils.py.

These complement the happy-path tests in test_time_utils.py which cover
common ISO 8601 formats. This file focuses on malformed inputs, None,
non-string types, and other edge cases.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.secuscan.time_utils import parse_to_utc


class TestParseToUtcEdgeCases:
    """Edge case tests for parse_to_utc."""

    def test_none_returns_none(self):
        """parse_to_utc(None) returns None without raising."""
        result = parse_to_utc(None)
        assert result is None

    def test_empty_string_returns_none(self):
        """parse_to_utc('') returns None without raising."""
        result = parse_to_utc("")
        assert result is None

    def test_whitespace_only_string_returns_none(self):
        """parse_to_utc('   ') (whitespace only) returns None."""
        result = parse_to_utc("   ")
        assert result is None

    def test_garbage_string_returns_none(self):
        """parse_to_utc('not-a-date') returns None without raising."""
        result = parse_to_utc("not-a-date")
        assert result is None

    def test_random_text_returns_none(self):
        """parse_to_utc('hello world') returns None."""
        result = parse_to_utc("hello world")
        assert result is None

    def test_integer_timestamp_returns_utc(self):
        """parse_to_utc(1762108800) treats the integer as a Unix timestamp."""
        result = parse_to_utc(1762108800)
        assert result is not None
        assert result.tzinfo is not None
        # 1762108800 is a valid Unix timestamp for 2025-11-02 UTC
        assert result.year == 2025

    def test_float_timestamp_returns_utc(self):
        """parse_to_utc(1762108800.5) treats the float as a Unix timestamp."""
        result = parse_to_utc(1762108800.5)
        assert result is not None
        assert result.tzinfo is not None

    def test_now_string_returns_current_time(self):
        """parse_to_utc('now') returns the current UTC time."""
        before = datetime.now(timezone.utc)
        result = parse_to_utc("now")
        after = datetime.now(timezone.utc)
        assert result is not None
        assert result.tzinfo is not None
        # Result should be between before and after (within a few seconds)
        assert before <= result <= after or after <= result <= before

    def test_list_input_returns_none(self):
        """parse_to_utc([1, 2, 3]) converts to string '[1, 2, 3]' which is not a valid date."""
        result = parse_to_utc([1, 2, 3])
        assert result is None

    def test_boolean_true_returns_utc_epoch_plus_one_second(self):
        """parse_to_utc(True) treats True as int(1), i.e. Unix epoch + 1 second."""
        result = parse_to_utc(True)
        assert result is not None
        assert result.tzinfo is not None
        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 1

    def test_boolean_false_returns_utc_epoch(self):
        """parse_to_utc(False) treats False as int(0), i.e. Unix epoch (1970-01-01 00:00:00 UTC)."""
        result = parse_to_utc(False)
        assert result is not None
        assert result.tzinfo is not None
        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
