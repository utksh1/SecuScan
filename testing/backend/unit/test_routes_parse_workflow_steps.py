"""
Unit tests for _parse_workflow_steps in backend/secuscan/routes.py.

Tests the workflow step normalization helper that parses three input types
(list, JSON string, falsy) and validates via WorkflowStep Pydantic model.
"""

from backend.secuscan.routes_workflow_helpers import _parse_workflow_steps


class TestParseWorkflowSteps:
    def test_already_a_list_passed_through(self):
        steps = [
            {"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}, "preset": "default"},
            {"plugin_id": "nikto", "inputs": {"target": "example.com"}},
        ]
        result = _parse_workflow_steps(steps)
        assert len(result) == 2
        assert result[0]["plugin_id"] == "nmap"
        assert result[1]["plugin_id"] == "nikto"

    def test_json_string_parsed_correctly(self):
        import json
        raw = json.dumps([
            {"plugin_id": "zap", "inputs": {"url": "http://test.com"}}
        ])
        result = _parse_workflow_steps(raw)
        assert len(result) == 1
        assert result[0]["plugin_id"] == "zap"

    def test_none_input_returns_empty_list(self):
        assert _parse_workflow_steps(None) == []

    def test_empty_string_returns_empty_list(self):
        assert _parse_workflow_steps("") == []

    def test_single_valid_step_normalized(self):
        result = _parse_workflow_steps([
            {"plugin_id": "nmap", "inputs": {"target": "8.8.8.8"}, "preset": "fast"}
        ])
        assert len(result) == 1
        assert result[0]["plugin_id"] == "nmap"
        assert result[0]["inputs"] == {"target": "8.8.8.8"}
        assert result[0]["preset"] == "fast"

    def test_missing_optional_fields_defaults(self):
        result = _parse_workflow_steps([{"plugin_id": "test"}])
        assert len(result) == 1
        assert result[0]["plugin_id"] == "test"
        # preset defaults to None
        assert "preset" in result[0]
        # inputs defaults to {}
        assert result[0]["inputs"] == {}

    def test_null_plugin_id_converted_to_empty_string(self):
        result = _parse_workflow_steps([{"plugin_id": None, "inputs": {}}])
        assert len(result) == 1
        assert result[0]["plugin_id"] == ""

    def test_non_dict_step_skipped(self):
        result = _parse_workflow_steps([
            {"plugin_id": "good"},
            "not a dict",
            123,
            None,
            {"plugin_id": "also_good"},
        ])
        assert len(result) == 2
        assert result[0]["plugin_id"] == "good"
        assert result[1]["plugin_id"] == "also_good"

    def test_invalid_step_skipped_gracefully(self):
        # Empty plugin_id is accepted (converted to "")
        result = _parse_workflow_steps([{"inputs": {}}])
        assert len(result) == 1

    def test_mixed_valid_and_invalid_steps(self):
        result = _parse_workflow_steps([
            {"plugin_id": "valid1"},
            "string_step",
            {"plugin_id": "valid2", "inputs": {"a": 1}},
        ])
        assert len(result) == 2

    def test_empty_inputs_dict_preserved(self):
        result = _parse_workflow_steps([{"plugin_id": "x", "inputs": {}}])
        assert len(result) == 1
        assert result[0]["inputs"] == {}
