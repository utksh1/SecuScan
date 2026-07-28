"""Unit tests for _parse_discovered_at in backend/secuscan/executor.py."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from backend.secuscan.executor_helpers import _parse_discovered_at


class TestParseDiscoveredAt:
    def test_iso_string_returns_aware_datetime(self):
        finding = {"discovered_at": "2026-01-15T10:30:00Z"}
        result = _parse_discovered_at(finding)
        assert result.tzinfo is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_iso_string_with_offset(self):
        finding = {"discovered_at": "2026-03-20T14:00:00+05:30"}
        result = _parse_discovered_at(finding)
        assert result.tzinfo is not None

    def test_timestamp_integer(self):
        finding = {"discovered_at": 1704067200}  # 2024-01-01 00:00:00 UTC
        result = _parse_discovered_at(finding)
        assert result.tzinfo is not None

    def test_datetime_object_aware(self):
        aware_dt = datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        finding = {"discovered_at": aware_dt}
        result = _parse_discovered_at(finding)
        assert result == aware_dt
        assert result.tzinfo is not None

    def test_naive_datetime_normalized_to_utc(self):
        naive_dt = datetime(2026, 6, 15, 12, 0, 0)
        finding = {"discovered_at": naive_dt}
        result = _parse_discovered_at(finding)
        assert result.tzinfo is not None

    def test_missing_discovered_at_falls_back_to_utc_now(self):
        fallback = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("backend.secuscan.time_utils.utc_now", return_value=fallback):
            result = _parse_discovered_at({})
            assert result == fallback

    def test_none_discovered_at_falls_back_to_utc_now(self):
        fallback = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("backend.secuscan.time_utils.utc_now", return_value=fallback):
            result = _parse_discovered_at({"discovered_at": None})
            assert result == fallback

    def test_invalid_string_falls_back_to_utc_now(self):
        fallback = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("backend.secuscan.time_utils.utc_now", return_value=fallback):
            result = _parse_discovered_at({"discovered_at": "not-a-date"})
            assert result == fallback

    def test_empty_string_falls_back_to_utc_now(self):
        fallback = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
        with patch("backend.secuscan.time_utils.utc_now", return_value=fallback):
            result = _parse_discovered_at({"discovered_at": ""})
            assert result == fallback
