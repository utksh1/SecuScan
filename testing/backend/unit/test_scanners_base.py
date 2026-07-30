"""
Unit tests for BaseScanner pure helper methods in backend/secuscan/scanners/base.py.

Covers:
- update_progress: clamps input to [0.0, 1.0]
- get_progress: returns the clamped progress value
- normalize_severity: maps severity strings to canonical values

The abstract methods (run, name, category) and _execute_command are integration-level
and are NOT tested here.
"""

from backend.secuscan.scanners.base import BaseScanner


class _ConcreteScanner(BaseScanner):
    """Minimal concrete subclass for testing helper methods."""

    @property
    def name(self) -> str:
        return "TestScanner"

    @property
    def category(self) -> str:
        return "Test"

    async def run(self, target: str, inputs: dict) -> dict:
        return {}


# ---------------------------------------------------------------------------
# update_progress
# ---------------------------------------------------------------------------


class TestUpdateProgress:
    def test_negative_clamped_to_zero(self):
        scanner = _ConcreteScanner("task1", None)
        scanner.update_progress(-0.5)
        assert scanner.get_progress() == 0.0

    def test_large_negative_clamped(self):
        scanner = _ConcreteScanner("task2", None)
        scanner.update_progress(-999.0)
        assert scanner.get_progress() == 0.0

    def test_zero_unchanged(self):
        scanner = _ConcreteScanner("task3", None)
        scanner.update_progress(0.0)
        assert scanner.get_progress() == 0.0

    def test_in_range_unchanged(self):
        scanner = _ConcreteScanner("task4", None)
        scanner.update_progress(0.5)
        assert scanner.get_progress() == 0.5

    def test_one_unchanged(self):
        scanner = _ConcreteScanner("task5", None)
        scanner.update_progress(1.0)
        assert scanner.get_progress() == 1.0

    def test_over_one_clamped(self):
        scanner = _ConcreteScanner("task6", None)
        scanner.update_progress(1.5)
        assert scanner.get_progress() == 1.0

    def test_very_large_value_clamped(self):
        scanner = _ConcreteScanner("task7", None)
        scanner.update_progress(999.0)
        assert scanner.get_progress() == 1.0


# ---------------------------------------------------------------------------
# get_progress
# ---------------------------------------------------------------------------


class TestGetProgress:
    def test_initial_progress_is_zero(self):
        scanner = _ConcreteScanner("task8", None)
        assert scanner.get_progress() == 0.0

    def test_reflects_last_update_progress_call(self):
        scanner = _ConcreteScanner("task9", None)
        scanner.update_progress(0.75)
        assert scanner.get_progress() == 0.75

    def test_multiple_updates_accumulate(self):
        scanner = _ConcreteScanner("task10", None)
        scanner.update_progress(0.1)
        assert scanner.get_progress() == 0.1
        scanner.update_progress(0.3)
        assert scanner.get_progress() == 0.3
        scanner.update_progress(0.8)
        assert scanner.get_progress() == 0.8


# ---------------------------------------------------------------------------
# normalize_severity
# ---------------------------------------------------------------------------


class TestNormalizeSeverity:
    def test_critical(self):
        scanner = _ConcreteScanner("task11", None)
        assert scanner.normalize_severity("critical") == "critical"

    def test_high(self):
        scanner = _ConcreteScanner("task12", None)
        assert scanner.normalize_severity("high") == "high"

    def test_medium(self):
        scanner = _ConcreteScanner("task13", None)
        assert scanner.normalize_severity("medium") == "medium"

    def test_moderate_normalised_to_medium(self):
        scanner = _ConcreteScanner("task14", None)
        assert scanner.normalize_severity("moderate") == "medium"

    def test_low(self):
        scanner = _ConcreteScanner("task15", None)
        assert scanner.normalize_severity("low") == "low"

    def test_info(self):
        scanner = _ConcreteScanner("task16", None)
        assert scanner.normalize_severity("info") == "info"

    def test_informational_normalised_to_info(self):
        scanner = _ConcreteScanner("task17", None)
        assert scanner.normalize_severity("informational") == "info"

    def test_note_normalised_to_info(self):
        scanner = _ConcreteScanner("task18", None)
        assert scanner.normalize_severity("note") == "info"

    def test_unknown_defaults_to_info(self):
        scanner = _ConcreteScanner("task19", None)
        assert scanner.normalize_severity("nonexistent") == "info"
        assert scanner.normalize_severity("") == "info"
        assert scanner.normalize_severity("xyz") == "info"

    def test_uppercase_known_values_normalised(self):
        # lowercasing happens before mapping lookup
        scanner = _ConcreteScanner("task22", None)
        assert scanner.normalize_severity("CRITICAL") == "critical"
        assert scanner.normalize_severity("HIGH") == "high"

    def test_case_insensitive(self):
        scanner = _ConcreteScanner("task20", None)
        assert scanner.normalize_severity("Critical") == "critical"
        assert scanner.normalize_severity("HIGH") == "high"
        assert scanner.normalize_severity("Medium") == "medium"

    def test_non_string_input(self):
        scanner = _ConcreteScanner("task21", None)
        assert scanner.normalize_severity(123) == "info"