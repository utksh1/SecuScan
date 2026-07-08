"""
Unit tests for backend/secuscan/risk_scoring.py's _recency_detail helper.

Tests the human-readable recency explanation generator. This is a pure
function, so these tests run with --noconftest (no FastAPI dependencies
needed) since risk_scoring.py only depends on stdlib.
"""

from datetime import datetime, timedelta, timezone

import pytest

from backend.secuscan.risk_scoring import _recency_detail


class TestRecencyDetail:
    def test_none_discovered_at_returns_moderate_recency_message(self):
        """When discovered_at is None, a moderate-recency fallback message is returned."""
        result = _recency_detail(None, 5.0)
        assert result == "No discovery date — assumed moderate recency"

    def test_future_date_returns_very_recent_message(self):
        """A discovered_at timestamp in the future is treated as very recent."""
        future = datetime.now(timezone.utc) + timedelta(days=3)
        result = _recency_detail(future, 10.0)
        assert result == "Discovered in the future — treated as very recent"

    def test_today_returns_maximum_recency_message(self):
        """A discovered_at timestamp from today (0 days ago) returns the max-score message."""
        now = datetime.now(timezone.utc)
        result = _recency_detail(now, 10.0)
        assert result == "Discovered today — maximum recency score"

    def test_yesterday_returns_singular_day_message(self):
        """Exactly 1 day ago uses singular 'day' wording with the recency score."""
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        result = _recency_detail(yesterday, 7.5)
        assert result == "Discovered 1 day ago — recency score 7.5/10"

    def test_multiple_days_ago_returns_plural_days_message(self):
        """More than 1 day ago uses plural 'days' wording with the recency score."""
        ten_days_ago = datetime.now(timezone.utc) - timedelta(days=10)
        result = _recency_detail(ten_days_ago, 5.0)
        assert result == "Discovered 10 days ago — recency score 5.0/10"

    def test_many_days_ago_returns_plural_days_message(self):
        """A much older date (well past a year) still uses the plural days format."""
        long_ago = datetime.now(timezone.utc) - timedelta(days=400)
        result = _recency_detail(long_ago, 1.0)
        assert result == "Discovered 400 days ago — recency score 1.0/10"

    def test_naive_datetime_is_treated_as_utc(self):
        """A naive (non-tz-aware) datetime is assumed UTC and handled without error."""
        naive_yesterday = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        result = _recency_detail(naive_yesterday, 7.5)
        assert result == "Discovered 1 day ago — recency score 7.5/10"

    def test_non_utc_timezone_is_normalized_correctly(self):
        """A tz-aware datetime in a non-UTC timezone is normalized before day-diffing."""
        ist = timezone(timedelta(hours=5, minutes=30))
        # 1 day ago in IST should still resolve to ~1 day ago once normalized to UTC.
        one_day_ago_ist = datetime.now(ist) - timedelta(days=1)
        result = _recency_detail(one_day_ago_ist, 7.5)
        assert result == "Discovered 1 day ago — recency score 7.5/10"

    def test_recency_score_is_formatted_to_one_decimal_place(self):
        """The rv value passed in is always rendered with exactly one decimal place."""
        two_days_ago = datetime.now(timezone.utc) - timedelta(days=2)
        result = _recency_detail(two_days_ago, 5)
        assert result == "Discovered 2 days ago — recency score 5.0/10"