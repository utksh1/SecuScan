"""
Unit tests for routes.py JSON deserialization helpers.
"""
import pytest

from backend.secuscan.routes import (
    _json_payload,
    _serialize_workflow,
    iter_raw_output_chunks,
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


class TestJsonPayload:
    def test_returns_json_dumps_when_value_is_not_none(self):
        """_json_payload returns json.dumps of value when value is not None."""
        result = _json_payload({"key": "value"}, '{}')
        assert result == '{"key": "value"}'

    def test_returns_parsed_fallback_when_value_is_none(self):
        """_json_payload returns json.dumps of parsed fallback when value is None."""
        result = _json_payload(None, '{"fallback": true}')
        assert result == '{"fallback": true}'

    def test_returns_empty_list_when_value_is_none_and_fallback_is_empty_json(self):
        """_json_payload returns [] for None with empty-list fallback."""
        result = _json_payload(None, '[]')
        assert result == '[]'

    def test_returns_string_when_value_is_string(self):
        """_json_payload json-encodes a string value."""
        result = _json_payload("hello", '{}')
        assert result == '"hello"'

    def test_returns_int_when_value_is_int(self):
        """_json_payload json-encodes an int value."""
        result = _json_payload(42, '{}')
        assert result == '42'


class TestSerializeWorkflow:
    def test_returns_required_keys(self):
        """_serialize_workflow returns id, name, schedule_seconds, enabled, steps, etc."""
        row = {"id": "w1", "name": "Nightly Scan", "schedule_seconds": 3600, "enabled": 1}
        result = _serialize_workflow(row)
        assert result["id"] == "w1"
        assert result["name"] == "Nightly Scan"
        assert result["schedule_seconds"] == 3600
        assert result["enabled"] is True
        assert "steps" in result
        assert "created_at" in result
        assert "last_run_at" in result
        assert "queued_task_ids" in result

    def test_steps_parsed_from_steps_json(self):
        """_serialize_workflow calls _parse_workflow_steps on steps_json."""
        row = {
            "id": "w1", "name": "Test", "enabled": False,
            "steps_json": '[{"plugin_id": "nmap", "inputs": {}}]',
        }
        result = _serialize_workflow(row)
        assert len(result["steps"]) == 1
        assert result["steps"][0]["plugin_id"] == "nmap"

    def test_queued_task_ids_defaults_to_empty_list(self):
        """_serialize_workflow returns [] for queued_task_ids when not provided."""
        row = {"id": "w1", "name": "Test", "enabled": False}
        result = _serialize_workflow(row)
        assert result["queued_task_ids"] == []

    def test_queued_task_ids_can_be_overridden(self):
        """_serialize_workflow accepts an optional queued_task_ids list."""
        row = {"id": "w1", "name": "Test", "enabled": False}
        result = _serialize_workflow(row, queued_task_ids=["t1", "t2"])
        assert result["queued_task_ids"] == ["t1", "t2"]

    def test_missing_optional_fields_handled_gracefully(self):
        """_serialize_workflow handles rows with missing optional fields."""
        row = {"id": "w1", "name": "Minimal"}
        result = _serialize_workflow(row)
        assert result["id"] == "w1"
        assert result["name"] == "Minimal"
        assert result["schedule_seconds"] is None
        assert result["enabled"] is False
        assert result["created_at"] is None
        assert result["last_run_at"] is None


class TestIterRawOutputChunks:
    def test_yields_single_chunk_for_small_file(self, tmp_path):
        """A file smaller than chunk_size yields exactly one chunk."""
        path = tmp_path / "output.txt"
        path.write_text("hello world", encoding="utf-8")
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=1024))
        assert len(chunks) == 1
        assert chunks[0] == "hello world"

    def test_yields_multiple_chunks_for_large_file(self, tmp_path):
        """A file larger than chunk_size yields multiple chunks."""
        path = tmp_path / "output.txt"
        content = "x" * 300
        path.write_text(content, encoding="utf-8")
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=100))
        assert len(chunks) == 3
        assert "".join(chunks) == content

    def test_last_chunk_smaller_than_chunk_size(self, tmp_path):
        """The final chunk may be smaller than chunk_size."""
        path = tmp_path / "output.txt"
        content = "abc"
        path.write_text(content, encoding="utf-8")
        chunks = list(iter_raw_output_chunks(str(path), chunk_size=2))
        assert len(chunks) == 2
        assert chunks[0] == "ab"
        assert chunks[1] == "c"

    def test_empty_file_yields_no_chunks(self, tmp_path):
        """An empty file produces no chunks."""
        path = tmp_path / "empty.txt"
        path.write_text("", encoding="utf-8")
        chunks = list(iter_raw_output_chunks(str(path)))
        assert chunks == []

    def test_unicode_handled_without_crash(self, tmp_path):
        """Unicode content is decoded without raising an exception."""
        path = tmp_path / "unicode.txt"
        path.write_text("hello world", encoding="utf-8")
        chunks = list(iter_raw_output_chunks(str(path)))
        assert len(chunks) == 1
        assert "hello" in chunks[0]
