"""
Unit tests for backend.secuscan.platform_resources_helpers sync helpers.
The sync helpers were extracted to platform_resources_helpers.py so they can be
imported and tested without loading aiosqlite.
"""

import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from backend.secuscan.platform_resources_helpers import (
    _stable_asset_id,
    _deserialize_resource_row,
    deserialize_resource_rows,
    serialize_execution_context,
)


class TestStableAssetId:
    def test_same_inputs_produce_same_id(self):
        id1 = _stable_asset_id("https://example.com", "example.com", 443, "https")
        id2 = _stable_asset_id("https://example.com", "example.com", 443, "https")
        assert id1 == id2

    def test_different_targets_produce_different_ids(self):
        id1 = _stable_asset_id("https://example.com", "example.com", 443, "https")
        id2 = _stable_asset_id("https://test.com", "test.com", 443, "https")
        assert id1 != id2

    def test_none_inputs_do_not_crash(self):
        _stable_asset_id(None, None, None, None)

    def test_id_starts_with_asset_prefix(self):
        asset_id = _stable_asset_id("https://example.com", "example.com", 443, "https")
        assert asset_id.startswith("asset:")

    def test_case_insensitive_for_host(self):
        id1 = _stable_asset_id("https://EXAMPLE.COM", "EXAMPLE.COM", 443, "https")
        id2 = _stable_asset_id("https://example.com", "example.com", 443, "https")
        assert id1 == id2


class TestDeserializeResourceRow:
    def test_deserializes_json_columns(self):
        row = {
            "id": "test-123",
            "name": "Test Policy",
            "metadata_json": '{"key": "value", "nested": {"a": 1}}',
            "allowed_targets_json": '["https://example.com"]',
        }
        result = _deserialize_resource_row(row)
        assert result["metadata"] == {"key": "value", "nested": {"a": 1}}
        assert result["allowed_targets"] == ["https://example.com"]
        # original _json key should still exist
        assert "metadata_json" in result

    def test_rows_without_json_columns_pass_through(self):
        row = {"id": "test-123", "name": "Simple"}
        result = _deserialize_resource_row(row)
        assert result == row

    def test_invalid_json_keeps_original_value(self):
        row = {
            "id": "test-123",
            "metadata_json": "not valid json {{{",
        }
        result = _deserialize_resource_row(row)
        # keeps original string when JSON is invalid
        assert "metadata_json" in result

    def test_none_input_returns_none(self):
        result = _deserialize_resource_row(None)
        assert result is None


class TestDeserializeResourceRows:
    def test_deserializes_list_of_rows(self):
        rows = [
            {"id": "1", "metadata_json": '{"a": 1}'},
            {"id": "2", "name": "no json"},
            {"id": "3", "metadata_json": '{"b": 2}'},
        ]
        results = deserialize_resource_rows(rows)
        assert len(results) == 3
        assert results[0]["metadata"] == {"a": 1}
        assert results[2]["metadata"] == {"b": 2}

    def test_skips_none_results(self):
        rows = [
            {"id": "1", "metadata_json": '{"a": 1}'},
            None,
            {"id": "2"},
        ]
        results = deserialize_resource_rows(rows)
        assert len(results) == 2

    def test_empty_list_returns_empty(self):
        assert deserialize_resource_rows([]) == []


class TestSerializeExecutionContext:
    def test_with_dict(self):
        result = serialize_execution_context({"validation_mode": "proof"})
        parsed = json.loads(result)
        assert parsed["validation_mode"] == "proof"

    def test_with_none(self):
        result = serialize_execution_context(None)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)
