"""
Tests for backend.secuscan.platform_resources pure helper functions.

Covers:
- _stable_asset_id: deterministic SHA-based asset ID generation
- serialize_execution_context: ExecutionContext -> JSON string
- _deserialize_resource_row: _json suffix columns deserialized; None passthrough
- deserialize_resource_rows: list of rows, skips None
"""

from backend.secuscan.platform_resources_helpers import (
    _stable_asset_id,
    serialize_execution_context,
    _deserialize_resource_row,
    deserialize_resource_rows,
)
from backend.secuscan.models import ExecutionContext, ValidationMode, EvidenceLevel


class TestStableAssetId:
    def test_deterministic_same_inputs(self):
        a = _stable_asset_id("http://example.com", "93.184.216.34", 443, "https")
        b = _stable_asset_id("http://example.com", "93.184.216.34", 443, "https")
        assert a == b

    def test_different_inputs_different_ids(self):
        a = _stable_asset_id("http://example.com", "93.184.216.34", 443, "https")
        b = _stable_asset_id("http://example.org", "93.184.216.34", 443, "https")
        assert a != b

    def test_port_difference_produces_different_id(self):
        a = _stable_asset_id("example.com", "1.2.3.4", 80, "http")
        b = _stable_asset_id("example.com", "1.2.3.4", 443, "http")
        assert a != b

    def test_empty_and_none_values_handled_gracefully(self):
        # Should not raise, should produce a valid string
        result = _stable_asset_id("", None, None, None)
        assert isinstance(result, str)
        assert result.startswith("asset:")

    def test_result_format_is_asset_prefix(self):
        result = _stable_asset_id("example.com", "1.2.3.4", 80, "http")
        assert result.startswith("asset:")
        # SHA-1 truncated to 16 hex chars = 16 chars after "asset:"
        assert len(result) == len("asset:") + 16


class TestSerializeExecutionContext:
    def test_with_execution_context_instance(self):
        ctx = ExecutionContext(
            validation_mode=ValidationMode.PROOF,
            evidence_level=EvidenceLevel.FULL,
        )
        result = serialize_execution_context(ctx)
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert parsed["validation_mode"] == "proof"

    def test_with_plain_dict(self):
        raw = {"validation_mode": "detect_only", "evidence_level": "standard"}
        result = serialize_execution_context(raw)
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert parsed["validation_mode"] == "detect_only"

    def test_with_none_returns_default_dump(self):
        result = serialize_execution_context(None)
        assert isinstance(result, str)
        import json
        parsed = json.loads(result)
        assert "validation_mode" in parsed


class TestDeserializeResourceRow:
    def test_none_input_returns_none(self):
        assert _deserialize_resource_row(None) is None

    def test_json_columns_deserialized(self):
        row = {
            "id": "abc123",
            "metadata_json": '{"key": "value"}',
            "risk_factors_json": '["low", "high"]',
        }
        result = _deserialize_resource_row(row)
        assert result["metadata"] == {"key": "value"}
        assert result["risk_factors"] == ["low", "high"]

    def test_invalid_json_falls_back_to_raw_string(self):
        row = {
            "id": "abc123",
            "metadata_json": "not valid json {",
        }
        result = _deserialize_resource_row(row)
        # Falls back to raw string value
        assert result["metadata"] == "not valid json {"

    def test_non_json_columns_preserved(self):
        row = {
            "id": "abc123",
            "name": "Test Asset",
            "metadata_json": '{"key": "value"}',
        }
        result = _deserialize_resource_row(row)
        assert result["id"] == "abc123"
        assert result["name"] == "Test Asset"


class TestDeserializeResourceRows:
    def test_applies_to_each_row(self):
        rows = [
            {"id": "1", "metadata_json": '{"a": 1}'},
            {"id": "2", "metadata_json": '{"b": 2}'},
        ]
        results = deserialize_resource_rows(rows)
        assert len(results) == 2
        assert results[0]["metadata"] == {"a": 1}
        assert results[1]["metadata"] == {"b": 2}

    def test_skips_none_rows(self):
        rows = [
            {"id": "1", "metadata_json": '{"a": 1}'},
            None,
            {"id": "2", "metadata_json": '{"b": 2}'},
        ]
        results = deserialize_resource_rows(rows)
        assert len(results) == 2
        assert results[0]["id"] == "1"
        assert results[1]["id"] == "2"

    def test_empty_list(self):
        results = deserialize_resource_rows([])
        assert results == []
