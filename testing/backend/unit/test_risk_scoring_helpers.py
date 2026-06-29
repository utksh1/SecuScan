"""
Unit tests for risk_scoring internal pure helpers.

Covers _clamp, _severity_score, _recency_score, _confidence_score
from backend.secuscan.risk_scoring.
"""

import pytest
from datetime import datetime, timezone, timedelta


class TestClamp:
    def test_within_range_returns_value(self):
        """When value is within bounds, it is returned unchanged."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(5.0, 0.0, 10.0) == 5.0

    def test_below_lo_returns_lo(self):
        """When value is below lo, lo is returned."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(-3.0, 0.0, 10.0) == 0.0

    def test_above_hi_returns_hi(self):
        """When value is above hi, hi is returned."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(15.0, 0.0, 10.0) == 10.0

    def test_default_bounds_are_zero_and_ten(self):
        """Default bounds are 0.0 and 10.0."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(5.0) == 5.0
        assert _clamp(-1.0) == 0.0
        assert _clamp(15.0) == 10.0

    def test_at_boundary_returns_boundary(self):
        """Values exactly at boundaries are returned unchanged."""
        from backend.secuscan.risk_scoring import _clamp
        assert _clamp(0.0, 0.0, 10.0) == 0.0
        assert _clamp(10.0, 0.0, 10.0) == 10.0


class TestSeverityScore:
    def test_critical_returns_10(self):
        """Severity 'critical' maps to 10.0."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("critical") == 10.0

    def test_high_returns_7_5(self):
        """Severity 'high' maps to 7.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("high") == 7.5

    def test_medium_returns_5(self):
        """Severity 'medium' maps to 5.0."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("medium") == 5.0

    def test_low_returns_2_5(self):
        """Severity 'low' maps to 2.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("low") == 2.5

    def test_info_returns_0_5(self):
        """Severity 'info' maps to 0.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("info") == 0.5

    def test_unknown_defaults_to_0_5(self):
        """Unknown severity defaults to 0.5."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("unknown") == 0.5
        assert _severity_score("") == 0.5

    def test_case_insensitive(self):
        """Severity matching is case-insensitive."""
        from backend.secuscan.risk_scoring import _severity_score
        assert _severity_score("CRITICAL") == 10.0
        assert _severity_score("High") == 7.5


class TestRecencyScore:
    def test_none_returns_5(self):
        """When discovered_at is None, score is 5.0."""
        from backend.secuscan.risk_scoring import _recency_score
        assert _recency_score(None) == 5.0

    def test_recent_within_week_returns_10(self):
        """A discovery within 7 days returns 10.0."""
        from backend.secuscan.risk_scoring import _recency_score
        recent = datetime.now(timezone.utc) - timedelta(hours=1)
        assert _recency_score(recent) == 10.0

    def test_old_within_month_returns_7_5(self):
        """A discovery within 30 days returns 7.5."""
        from backend.secuscan.risk_scoring import _recency_score
        old = datetime.now(timezone.utc) - timedelta(days=15)
        assert _recency_score(old) == 7.5

    def test_old_within_quarter_returns_5(self):
        """A discovery within 90 days returns 5.0."""
        from backend.secuscan.risk_scoring import _recency_score
        old = datetime.now(timezone.utc) - timedelta(days=60)
        assert _recency_score(old) == 5.0


class TestConfidenceScore:
    def test_none_returns_5(self):
        """When confidence is None, score defaults to 5.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(None) == 5.0

    def test_1_returns_10(self):
        """Confidence of 1.0 maps to 10.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(1.0) == 10.0

    def test_0_returns_0(self):
        """Confidence of 0.0 maps to 0.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(0.0) == 0.0

    def test_0_5_returns_5(self):
        """Confidence of 0.5 maps to 5.0."""
        from backend.secuscan.risk_scoring import _confidence_score
        assert _confidence_score(0.5) == 5.0


class TestRecencyDetail:
    def test_none_discovered_at_returns_assumed_recency_message(self):
        """When discovered_at is None, returns the 'assumed moderate recency' message."""
        from backend.secuscan.risk_scoring import _recency_detail
        result = _recency_detail(None, 5.0)
        assert result == "No discovery date — assumed moderate recency"

    def test_future_date_returns_treated_as_recent_message(self):
        """A future discovered_at (negative days) returns 'treated as very recent'."""
        from backend.secuscan.risk_scoring import _recency_detail
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(days=5)
        result = _recency_detail(future, 10.0)
        assert "future" in result.lower() or "very recent" in result.lower()

    def test_today_returns_maximum_recency_message(self):
        """A discovered_at of today (0 days ago) returns the 'maximum recency' message."""
        from backend.secuscan.risk_scoring import _recency_detail
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone.utc) - timedelta(hours=2)
        result = _recency_detail(today, 10.0)
        assert "today" in result.lower()
        assert "maximum recency" in result.lower()

    def test_one_day_ago_includes_day_count(self):
        """A discovered_at of 1 day ago includes the day count in the message."""
        from backend.secuscan.risk_scoring import _recency_detail
        from datetime import datetime, timezone, timedelta
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        result = _recency_detail(yesterday, 10.0)
        assert "1 day ago" in result
        assert "10.0" in result

    def test_multiple_days_ago_includes_correct_count(self):
        """A discovered_at of multiple days ago includes the correct day count."""
        from backend.secuscan.risk_scoring import _recency_detail
        from datetime import datetime, timezone, timedelta
        for days, expected_rv in [(7, 7.5), (30, 7.5), (60, 5.0), (90, 5.0), (180, 2.5), (400, 1.0)]:
            past = datetime.now(timezone.utc) - timedelta(days=days)
            result = _recency_detail(past, expected_rv)
            assert str(days) in result, f"Expected {days} days in: {result}"
            assert f"{expected_rv:.1f}" in result, f"Expected rv {expected_rv} in: {result}"

    def test_naive_datetime_handled(self):
        """A naive (non-UTC) datetime is handled without raising."""
        from backend.secuscan.risk_scoring import _recency_detail
        from datetime import datetime, timedelta
        naive = datetime.now() - timedelta(days=10)
        result = _recency_detail(naive, 5.0)
        assert isinstance(result, str)
        assert len(result) > 0
