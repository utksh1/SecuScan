"""
Unit tests for routes.py JSON deserialization helpers.
"""
import pytest

from backend.secuscan.routes import (
    parse_json_fields,
    deserialize_finding_rows,
    deserialize_asset_service_rows,
    _parse_workflow_steps,
)


class TestParseJsonFields:
    def test_decodes_valid_json_string(self):
        rows = [{"field": '{"key": "val"}'}]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] == {"key": "val"}

    def test_skips_non_string_values(self):
        rows = [{"field": 42}]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] == 42

    def test_skips_missing_fields(self):
        rows = [{}]
        result = parse_json_fields(rows, ["field"])
        assert result[0] == {}

    def test_handles_bad_json_unchanged(self):
        rows = [{"field": "not-json"}]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] == "not-json"

    def test_handles_none_value(self):
        rows = [{"field": None}]
        result = parse_json_fields(rows, ["field"])
        assert result[0]["field"] is None

    def test_multiple_rows_and_fields(self):
        rows = [
            {"a": '{"x":1}', "b": '{"y":2}'},
            {"a": '{"z":3}', "b": None},
        ]
        result = parse_json_fields(rows, ["a", "b"])
        assert result[0]["a"] == {"x": 1}
        assert result[0]["b"] == {"y": 2}
        assert result[1]["a"] == {"z": 3}
        assert result[1]["b"] is None

    def test_empty_rows_list(self):
        result = parse_json_fields([], ["field"])
        assert result == []


class TestDeserializeFindingRows:
    def test_renames_json_keys_to_clean_api_names(self):
        rows = [
            {
                "metadata_json": '{"src": "test"}',
                "risk_factors_json": '[]',
                "evidence_json": '[]',
                "asset_refs_json": '[]',
                "references_json": '[]',
                "corroborating_sources_json": '[]',
                "title": "Test Finding",
            }
        ]
        result = deserialize_finding_rows(rows)
        f = result[0]
        assert "metadata" in f
        assert "metadata_json" not in f
        assert f["metadata"] == {"src": "test"}
        assert "risk_factors" in f
        assert "evidence" in f
        assert "asset_refs" in f
        assert "references" in f
        assert "corroborating_sources" in f
        assert f["title"] == "Test Finding"

    def test_preserves_non_json_fields(self):
        rows = [{"title": "Hello", "severity": "high", "metadata_json": "{}"}]
        result = deserialize_finding_rows(rows)
        assert result[0]["title"] == "Hello"
        assert result[0]["severity"] == "high"

    def test_bad_json_in_metadata_field_unchanged(self):
        rows = [{"metadata_json": "broken{", "risk_factors_json": "also-broken{"}]
        result = deserialize_finding_rows(rows)
        assert result[0]["metadata"] == "broken{"
        assert result[0]["risk_factors"] == "also-broken{"


class TestDeserializeAssetServiceRows:
    def test_renames_metadata_json_and_cert_san_json(self):
        rows = [
            {
                "metadata_json": '{"host": "web"}',
                "cert_san_json": '["corp.local"]',
                "port": 443,
            }
        ]
        result = deserialize_asset_service_rows(rows)
        r = result[0]
        assert "metadata" in r
        assert "cert_san" in r
        assert r["metadata"] == {"host": "web"}
        assert r["cert_san"] == ["corp.local"]
        assert r["port"] == 443

    def test_bad_json_unchanged(self):
        rows = [{"metadata_json": "not-json"}]
        result = deserialize_asset_service_rows(rows)
        assert result[0]["metadata"] == "not-json"


class TestParseWorkflowSteps:
    def test_from_list_with_valid_step(self):
        steps = [{"plugin_id": "nmap", "inputs": {"target": "127.0.0.1"}}]
        result = _parse_workflow_steps(steps)
        assert len(result) == 1
        assert result[0]["plugin_id"] == "nmap"
        assert result[0]["inputs"] == {"target": "127.0.0.1"}

    def test_from_json_string(self):
        result = _parse_workflow_steps('[{"plugin_id": "nmap", "inputs": {}}]')
        assert len(result) == 1
        assert result[0]["plugin_id"] == "nmap"

    def test_from_none_returns_empty_list(self):
        result = _parse_workflow_steps(None)
        assert result == []

    def test_from_empty_string_returns_empty_list(self):
        result = _parse_workflow_steps("")
        assert result == []

    def test_skips_non_dict_items(self):
        result = _parse_workflow_steps(["not-a-dict", 123, {"plugin_id": "x", "inputs": {}}])
        assert len(result) == 1
        assert result[0]["plugin_id"] == "x"

    def test_dicts_without_plugin_id_produce_empty_plugin_id(self):
        # plugin_id="" is a valid WorkflowStep; the function coerces missing key to ""
        result = _parse_workflow_steps([{"inputs": {}}])
        assert len(result) == 1
        assert result[0]["plugin_id"] == ""

    def test_preserves_preset_field(self):
        steps = [{"plugin_id": "nmap", "inputs": {}, "preset": "fast", "execution_context": {}}]
        result = _parse_workflow_steps(steps)
        assert result[0]["preset"] == "fast"

    def test_empty_list_returns_empty(self):
        result = _parse_workflow_steps([])
        assert result == []
