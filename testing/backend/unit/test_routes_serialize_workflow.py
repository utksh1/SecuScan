"""
Unit tests for _serialize_workflow pure helper.

Imports the real production function from backend.secuscan.routes so a
regression in the workflow serialization logic is caught by these tests.

Note: routes.py has FastAPI imports so this module is only import-safe
when accessed through the re-exported _serialize_workflow via the
import-safe routes_json_helpers pattern.
"""
import pytest
from backend.secuscan.routes_workflow_helpers import _serialize_workflow, _parse_workflow_steps


# ---------------------------------------------------------------------------
# _serialize_workflow
# ---------------------------------------------------------------------------


def test_complete_row():
    """All fields from a complete row are serialized correctly."""
    row = {
        "id": "wf-1",
        "name": "Nightly Scan",
        "owner_id": "user-1",
        "enabled": True,
        "schedule_seconds": 3600,
        "created_at": "2026-06-22T00:00:00Z",
        "last_run_at": "2026-06-21T00:00:00Z",
        "steps_json": '[{"plugin_id": "nmap", "inputs": {}}]',
    }
    result = _serialize_workflow(row, queued_task_ids=["task-1"])
    assert result["id"] == "wf-1"
    assert result["name"] == "Nightly Scan"
    assert result["enabled"] is True
    assert result["schedule_seconds"] == 3600
    assert result["last_run_at"] == "2026-06-21T00:00:00Z"
    assert result["queued_task_ids"] == ["task-1"]
    assert result["created_at"] == "2026-06-22T00:00:00Z"
    # steps: parsed from steps_json
    assert len(result["steps"]) == 1
    assert result["steps"][0]["plugin_id"] == "nmap"


def test_steps_json_as_invalid_string():
    """Invalid steps_json string falls back to empty list."""
    row = {
        "id": "wf-1",
        "name": "Bad Steps",
        "owner_id": "user-1",
        "enabled": False,
        "steps_json": "not valid json",
    }
    result = _serialize_workflow(row)
    assert result["steps"] == []


def test_steps_json_as_valid_json_string():
    """Valid JSON string in steps_json is parsed."""
    row = {
        "id": "wf-1",
        "name": "Two Steps",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": '[{"plugin_id": "nmap", "inputs": {}}, {"plugin_id": "nikto", "inputs": {}}]',
    }
    result = _serialize_workflow(row)
    assert len(result["steps"]) == 2
    assert result["steps"][0]["plugin_id"] == "nmap"
    assert result["steps"][1]["plugin_id"] == "nikto"


def test_steps_json_none():
    """None steps_json is treated as an empty list."""
    row = {
        "id": "wf-1",
        "name": "No Steps",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": None,
    }
    result = _serialize_workflow(row)
    assert result["steps"] == []


def test_steps_json_empty_string():
    """Empty string steps_json is treated as an empty list."""
    row = {
        "id": "wf-1",
        "name": "Empty Steps",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": "",
    }
    result = _serialize_workflow(row)
    assert result["steps"] == []


def test_queued_task_ids_provided():
    """queued_task_ids are included in the output."""
    row = {
        "id": "wf-1",
        "name": "Running",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": "[]",
    }
    result = _serialize_workflow(row, queued_task_ids=["t1", "t2", "t3"])
    assert result["queued_task_ids"] == ["t1", "t2", "t3"]


def test_queued_task_ids_default_to_empty():
    """queued_task_ids defaults to an empty list when not provided."""
    row = {
        "id": "wf-1",
        "name": "No Tasks",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": "[]",
    }
    result = _serialize_workflow(row)
    assert result["queued_task_ids"] == []


def test_enabled_field_coerced_to_bool():
    """enabled field is coerced to bool (including from None)."""
    row_none = {
        "id": "wf-1",
        "name": "Test",
        "owner_id": "user-1",
        "enabled": None,
        "steps_json": "[]",
    }
    result_none = _serialize_workflow(row_none)
    assert result_none["enabled"] is False

    row_true = {
        "id": "wf-2",
        "name": "Test2",
        "owner_id": "user-1",
        "enabled": 1,
        "steps_json": "[]",
    }
    result_true = _serialize_workflow(row_true)
    assert result_true["enabled"] is True


def test_schedule_seconds_missing():
    """Missing schedule_seconds results in None in the output."""
    row = {
        "id": "wf-1",
        "name": "Manual",
        "owner_id": "user-1",
        "enabled": True,
        "steps_json": "[]",
    }
    result = _serialize_workflow(row)
    assert result["schedule_seconds"] is None


def test_missing_optional_fields():
    """Row missing optional fields uses .get() defaults."""
    row = {
        "id": "wf-min",
        "name": "Minimal",
        "steps_json": "[]",
    }
    result = _serialize_workflow(row)
    assert result["id"] == "wf-min"
    assert result["name"] == "Minimal"
    assert result["schedule_seconds"] is None
    assert result["enabled"] is False
    assert result["last_run_at"] is None
    assert result["created_at"] is None
    assert result["queued_task_ids"] == []


# ---------------------------------------------------------------------------
# _parse_workflow_steps (direct tests)
# ---------------------------------------------------------------------------


def test_parse_workflow_steps_list_input():
    """List input is passed through directly."""
    steps = [{"plugin_id": "nmap", "inputs": {"target": "example.com"}}]
    result = _parse_workflow_steps(steps)
    assert len(result) == 1
    assert result[0]["plugin_id"] == "nmap"


def test_parse_workflow_steps_none_input():
    """None input returns empty list."""
    assert _parse_workflow_steps(None) == []


def test_parse_workflow_steps_empty_string():
    """Empty string returns empty list."""
    assert _parse_workflow_steps("") == []


def test_parse_workflow_steps_invalid_json():
    """Invalid JSON string returns empty list."""
    assert _parse_workflow_steps("not json") == []


def test_parse_workflow_steps_non_dict_items_skipped():
    """Non-dict items in the list are skipped."""
    steps = ["not-a-dict", 123, {"plugin_id": "nmap", "inputs": {}}, None]
    result = _parse_workflow_steps(steps)
    assert len(result) == 1
    assert result[0]["plugin_id"] == "nmap"
    assert result[0]["inputs"] == {}
    assert "execution_context" in result[0]
