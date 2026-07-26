"""
Unit tests for backend/secuscan/routes_json_helpers _serialize_workflow edge cases.

_serialize_workflow serializes a database workflow row for the frontend API.
Existing tests cover the happy path; this file adds edge case coverage for
None optional fields, bool coercion, and missing keys.

Run with:
    python3 -m pytest testing/backend/unit/test_routes_workflow_serialize.py -v --noconftest
"""

from __future__ import annotations

from backend.secuscan.routes_json_helpers import _serialize_workflow


def _make_row(overrides=None):
    """Create a base workflow row dict with sensible defaults."""
    defaults = {
        "id": "wf-001",
        "name": "Nightly Scan",
        "schedule_seconds": 3600,
        "enabled": True,
        "steps_json": "[]",
        "created_at": "2024-01-01T00:00:00Z",
        "last_run_at": "2024-01-02T00:00:00Z",
    }
    if overrides:
        defaults.update(overrides)
    return defaults


class TestSerializeWorkflowOptionalFields:
    """Tests for handling of None/missing optional fields."""

    def test_none_schedule_seconds_returns_none(self):
        """_serialize_workflow with None schedule_seconds returns None for that field."""
        row = _make_row({"schedule_seconds": None})
        result = _serialize_workflow(row)
        assert result["schedule_seconds"] is None

    def test_none_created_at_returns_none(self):
        """_serialize_workflow with None created_at returns None for that field."""
        row = _make_row({"created_at": None})
        result = _serialize_workflow(row)
        assert result["created_at"] is None

    def test_none_last_run_at_returns_none(self):
        """_serialize_workflow with None last_run_at returns None for that field."""
        row = _make_row({"last_run_at": None})
        result = _serialize_workflow(row)
        assert result["last_run_at"] is None


class TestSerializeWorkflowEnabledCoercion:
    """Tests for bool coercion of the enabled field."""

    def test_enabled_string_zero_remains_truthy(self):
        """_serialize_workflow with enabled='0' (non-empty string) is truthy, coerces to True."""
        row = _make_row({"enabled": "0"})
        result = _serialize_workflow(row)
        assert result["enabled"] is True

    def test_enabled_string_one_becomes_true(self):
        """_serialize_workflow with enabled='1' must coerce to True."""
        row = _make_row({"enabled": "1"})
        result = _serialize_workflow(row)
        assert result["enabled"] is True

    def test_enabled_integer_zero_becomes_false(self):
        """_serialize_workflow with enabled=0 must coerce to False."""
        row = _make_row({"enabled": 0})
        result = _serialize_workflow(row)
        assert result["enabled"] is False

    def test_enabled_integer_one_becomes_true(self):
        """_serialize_workflow with enabled=1 must coerce to True."""
        row = _make_row({"enabled": 1})
        result = _serialize_workflow(row)
        assert result["enabled"] is True

    def test_enabled_none_becomes_false(self):
        """_serialize_workflow with enabled=None must coerce to False."""
        row = _make_row({"enabled": None})
        result = _serialize_workflow(row)
        assert result["enabled"] is False


class TestSerializeWorkflowMissingKeys:
    """Tests for handling of rows with missing optional keys."""

    def test_missing_optional_keys_do_not_raise(self):
        """_serialize_workflow must not raise KeyError for missing optional keys."""
        row = {
            "id": "wf-002",
            "name": "Daily Scan",
        }
        # Must not raise
        result = _serialize_workflow(row)
        assert result["id"] == "wf-002"
        assert result["name"] == "Daily Scan"

    def test_missing_optional_keys_have_default_values(self):
        """_serialize_workflow with missing optional keys returns appropriate defaults."""
        row = {"id": "wf-003", "name": "Minimal Scan"}
        result = _serialize_workflow(row)
        assert result["schedule_seconds"] is None
        assert result["enabled"] is False
        assert result["steps"] == []
        assert result["created_at"] is None
        assert result["last_run_at"] is None
        assert result["queued_task_ids"] == []


class TestSerializeWorkflowStepsParsing:
    """Tests for steps parsing edge cases."""

    def test_malformed_steps_json_returns_empty_steps(self):
        """_serialize_workflow with malformed steps_json skips the invalid steps."""
        row = _make_row({"steps_json": "not-valid-json"})
        result = _serialize_workflow(row)
        # Malformed JSON: _parse_workflow_steps catches JSONDecodeError and returns []
        assert result["steps"] == []

    def test_empty_steps_json_returns_empty_list(self):
        """_serialize_workflow with empty-string steps_json returns []."""
        row = _make_row({"steps_json": ""})
        result = _serialize_workflow(row)
        assert result["steps"] == []

    def test_non_list_json_steps_json_returns_empty(self):
        """_serialize_workflow with a non-list JSON value for steps returns []."""
        row = _make_row({"steps_json": '{"plugin_id": "nmap"}'})
        result = _serialize_workflow(row)
        # A JSON object is not a list, so _parse_workflow_steps skips it
        assert result["steps"] == []
