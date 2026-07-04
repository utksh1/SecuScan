"""
Unit tests for validate_schedule_timezone in workflows.py.
"""
import sys
from unittest.mock import MagicMock
sys.modules['aiosqlite'] = MagicMock()
sys.modules['database'] = MagicMock()

from backend.secuscan.workflows_helpers import validate_schedule_timezone


class TestValidateScheduleTimezone:
    def test_valid_iana_utc(self):
        """UTC is a valid timezone."""
        ok, msg = validate_schedule_timezone("UTC")
        assert ok is True

    def test_valid_iana_continent_city_india(self):
        """Asia/Kolkata is a valid IANA timezone (UTC+5:30)."""
        ok, msg = validate_schedule_timezone("Asia/Kolkata")
        assert ok is True

    def test_valid_iana_continent_city(self):
        """Continent/City form timezones are valid."""
        for tz in ("America/New_York", "Asia/Kolkata", "Europe/London", "Australia/Sydney"):
            ok, msg = validate_schedule_timezone(tz)
            assert ok is True, f"{tz} should be valid: {msg}"

    def test_invalid_random_string(self):
        """Random strings are rejected."""
        ok, msg = validate_schedule_timezone("NotATimezone")
        assert ok is False
        assert isinstance(msg, str)

    def test_invalid_empty_string(self):
        """Empty string is rejected."""
        ok, msg = validate_schedule_timezone("")
        assert ok is False

    def test_invalid_case_sensitivity(self):
        """Timezone names are case-sensitive."""
        ok_lower, _ = validate_schedule_timezone("america/new_york")
        ok_upper, _ = validate_schedule_timezone("America/New_York")
        assert ok_upper is True
        assert ok_lower is False

    def test_returns_tuple(self):
        """Return value is always a (bool, str) tuple."""
        result = validate_schedule_timezone("UTC")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], str)
