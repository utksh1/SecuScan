import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

from backend.secuscan.risk_scoring import _recency_detail


def test_no_discovery_date_returns_default():
    result = _recency_detail(None, 5.0)
    assert result == "No discovery date — assumed moderate recency"


def test_future_date_returns_future_message():
    future = datetime.now(timezone.utc) + timedelta(days=1)
    result = _recency_detail(future, 10.0)
    assert result == "Discovered in the future — treated as very recent"


def test_today_returns_today_message():
    today = datetime.now(timezone.utc)
    result = _recency_detail(today, 10.0)
    assert result == "Discovered today — maximum recency score"


def test_one_day_ago_returns_day_message():
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    result = _recency_detail(yesterday, 9.5)
    assert "1 day ago" in result
    assert "9.5/10" in result


def test_multiple_days_ago():
    five_days = datetime.now(timezone.utc) - timedelta(days=5)
    result = _recency_detail(five_days, 8.0)
    assert "5 days ago" in result
    assert "8.0/10" in result


def test_naive_datetime_gets_utc_tzinfo():
    naive = datetime.now() - timedelta(days=3)
    result = _recency_detail(naive, 7.0)
    assert "3 days ago" in result
    assert "7.0/10" in result
