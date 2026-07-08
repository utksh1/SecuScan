"""
Unit tests for backend.secuscan.finding_intelligence pure helpers.

Covers:
- _parse_timestamp normalises datetime, string, and edge-case inputs
- _stable_id produces consistent prefix:id format
- _normalize_severity maps all known severity strings correctly
- _severity_rank returns correct ordinals for each severity
"""

import pytest
from datetime import datetime, timezone

from backend.secuscan import finding_intelligence as fi


class TestParseTimestamp:
    def test_datetime_input(self):
        """_parse_timestamp returns ISO string for datetime input."""
        dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = fi._parse_timestamp(dt)
        assert isinstance(result, str)
        assert "2024-01-15" in result

    def test_z_suffix_string(self):
        """_parse_timestamp handles 'Z'-suffix ISO strings."""
        result = fi._parse_timestamp("2024-03-01T10:00:00Z")
        assert "2024-03-01" in result

    def test_none_input(self):
        """_parse_timestamp returns current ISO string for None."""
        result = fi._parse_timestamp(None)
        assert isinstance(result, str)
        assert "T" in result

    def test_empty_string_input(self):
        """_parse_timestamp returns current ISO string for empty string."""
        result = fi._parse_timestamp("")
        assert isinstance(result, str)
        assert "T" in result

    def test_unparseable_string(self):
        """_parse_timestamp falls back to current ISO string for unparseable input."""
        result = fi._parse_timestamp("not-a-date")
        assert isinstance(result, str)
        assert "T" in result


class TestStableId:
    def test_prefix_format(self):
        """_stable_id produces 'prefix:digest' format."""
        result = fi._stable_id("finding", "host", "path")
        assert ":" in result
        prefix, rest = result.split(":", 1)
        assert prefix == "finding"

    def test_same_inputs_same_id(self):
        """_stable_id is deterministic for identical inputs."""
        id1 = fi._stable_id("finding", "example.com", "/api/v1")
        id2 = fi._stable_id("finding", "example.com", "/api/v1")
        assert id1 == id2

    def test_different_inputs_different_id(self):
        """_stable_id produces different IDs for different inputs."""
        id1 = fi._stable_id("finding", "example.com", "/api/v1")
        id2 = fi._stable_id("finding", "example.com", "/api/v2")
        assert id1 != id2

    def test_empty_parts_are_treated_as_empty(self):
        """_stable_id handles empty or None parts."""
        id1 = fi._stable_id("finding", None, "")
        id2 = fi._stable_id("finding", "", "")
        assert isinstance(id1, str)
        assert id1 == id2


class TestNormalizeSeverity:
    def test_critical_high_medium_low_info(self):
        """_normalize_severity maps standard severity names correctly."""
        assert fi._normalize_severity("critical") == "critical"
        assert fi._normalize_severity("high") == "high"
        assert fi._normalize_severity("medium") == "medium"
        assert fi._normalize_severity("low") == "low"
        assert fi._normalize_severity("info") == "info"

    def test_aliases(self):
        """_normalize_severity maps common aliases to canonical values."""
        assert fi._normalize_severity("moderate") == "medium"
        assert fi._normalize_severity("informational") == "info"

    def test_case_insensitive(self):
        """_normalize_severity is case-insensitive."""
        assert fi._normalize_severity("CRITICAL") == "critical"
        assert fi._normalize_severity("High") == "high"

    def test_unknown_defaults_to_info(self):
        """_normalize_severity returns 'info' for unknown values."""
        assert fi._normalize_severity("unknown") == "info"
        assert fi._normalize_severity("") == "info"
        assert fi._normalize_severity(None) == "info"


class TestSeverityRank:
    def test_rank_order(self):
        """_severity_rank returns correct ordinals: critical > high > medium > low > info."""
        assert fi._severity_rank("critical") == 5
        assert fi._severity_rank("high") == 4
        assert fi._severity_rank("medium") == 3
        assert fi._severity_rank("low") == 2
        assert fi._severity_rank("info") == 1

    def test_unknown_defaults_to_info_rank(self):
        """_severity_rank returns 1 (info rank) for unknown severity."""
        assert fi._severity_rank("unknown") == 1
        assert fi._severity_rank("") == 1
