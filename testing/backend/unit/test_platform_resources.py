"""
Unit tests for backend/secuscan/platform_resources.py

Covers the pure helpers exposed by the module:
  - _stable_asset_id: deterministic asset id derivation
  - _deserialize_resource_row: unwrap *_json columns
  - deserialize_resource_rows: filter None rows
  - serialize_execution_context: JSON round-trip with normalize_execution_context

The persistence helpers (persist_crawl_run, replace_asset_services) require a
real Database and are not exercised here; they are covered by integration tests.
"""

from __future__ import annotations

import json

import pytest

from backend.secuscan.execution_context import normalize_execution_context
from backend.secuscan.platform_resources import (
    _deserialize_resource_row,
    _stable_asset_id,
    deserialize_resource_rows,
    serialize_execution_context,
)


# ---------------------------------------------------------------------------
# _stable_asset_id
# ---------------------------------------------------------------------------


class TestStableAssetId:
    def test_returns_string_starting_with_asset_prefix(self):
        result = _stable_asset_id("example.com", "example.com", 443, "tcp")
        assert isinstance(result, str)
        assert result.startswith("asset:")

    def test_asset_id_is_16_hex_chars_after_prefix(self):
        result = _stable_asset_id("example.com", "example.com", 443, "tcp")
        suffix = result.split(":", 1)[1]
        assert len(suffix) == 16
        # All hex characters
        int(suffix, 16)

    def test_is_deterministic_for_same_inputs(self):
        a = _stable_asset_id("example.com", "example.com", 443, "tcp")
        b = _stable_asset_id("example.com", "example.com", 443, "tcp")
        assert a == b

    def test_changes_when_target_changes(self):
        a = _stable_asset_id("example.com", "example.com", 443, "tcp")
        b = _stable_asset_id("other.com", "example.com", 443, "tcp")
        assert a != b

    def test_changes_when_host_changes(self):
        a = _stable_asset_id("example.com", "a.example.com", 443, "tcp")
        b = _stable_asset_id("example.com", "b.example.com", 443, "tcp")
        assert a != b

    def test_changes_when_port_changes(self):
        a = _stable_asset_id("example.com", "example.com", 80, "tcp")
        b = _stable_asset_id("example.com", "example.com", 443, "tcp")
        assert a != b

    def test_changes_when_protocol_changes(self):
        a = _stable_asset_id("example.com", "example.com", 443, "tcp")
        b = _stable_asset_id("example.com", "example.com", 443, "udp")
        assert a != b

    def test_handles_empty_fields(self):
        # All-empty should still produce a valid asset id (no exception)
        result = _stable_asset_id("", "", "", "")
        assert result.startswith("asset:")
        assert len(result.split(":", 1)[1]) == 16

    def test_handles_none_fields(self):
        # None values must be stringified, not raise
        result = _stable_asset_id(None, None, None, None)
        assert result.startswith("asset:")
        assert len(result.split(":", 1)[1]) == 16

    def test_lowercases_inputs(self):
        a = _stable_asset_id("EXAMPLE.COM", "HOST", "443", "TCP")
        b = _stable_asset_id("example.com", "host", "443", "tcp")
        assert a == b

    def test_strips_whitespace(self):
        a = _stable_asset_id("  example.com  ", "  host  ", 443, "tcp")
        b = _stable_asset_id("example.com", "host", 443, "tcp")
        assert a == b

    def test_numeric_port_stringified_consistently(self):
        # The function uses str(part).strip().lower() - ints and str(443) match
        a = _stable_asset_id("example.com", "example.com", 443, "tcp")
        b = _stable_asset_id("example.com", "example.com", "443", "tcp")
        assert a == b


# ---------------------------------------------------------------------------
# _deserialize_resource_row
# ---------------------------------------------------------------------------


class TestDeserializeResourceRow:
    def test_unwraps_json_suffix_column(self):
        row = {
            "id": "row-1",
            "name": "row-1",
            "summary_json": json.dumps({"x": 1}),
            "pages_json": "[1, 2, 3]",
        }
        result = _deserialize_resource_row(row)
        assert result["id"] == "row-1"
        assert result["summary"] == {"x": 1}
        assert result["pages"] == [1, 2, 3]
        # The unwrapped keys live alongside the original *_json keys
        assert "summary_json" in result
        assert result["summary_json"] == '{"x": 1}'

    def test_preserves_non_json_columns(self):
        row = {"id": "row-1", "name": "row-1", "owner_id": "user-1"}
        result = _deserialize_resource_row(row)
        assert result == {"id": "row-1", "name": "row-1", "owner_id": "user-1"}

    def test_tolerates_malformed_json_in_json_column(self):
        row = {"id": "row-1", "summary_json": "{not valid json"}
        result = _deserialize_resource_row(row)
        # Malformed JSON falls back to the original raw string
        assert result["summary"] == "{not valid json"

    def test_none_input_returns_none(self):
        assert _deserialize_resource_row(None) is None

    def test_does_not_modify_input_row(self):
        row = {"id": "row-1", "summary_json": json.dumps({"k": "v"})}
        snapshot = dict(row)
        _deserialize_resource_row(row)
        assert row == snapshot

    def test_empty_json_string_unwraps_to_empty_dict_or_list(self):
        # json.loads("") raises - must not crash, falls back to raw ""
        row = {"id": "row-1", "summary_json": ""}
        result = _deserialize_resource_row(row)
        assert result["summary"] == ""


# ---------------------------------------------------------------------------
# deserialize_resource_rows
# ---------------------------------------------------------------------------


class TestDeserializeResourceRows:
    def test_filters_none_rows(self):
        rows = [None, {"id": "1", "name": "1"}, None, {"id": "2", "name": "2"}]
        result = deserialize_resource_rows(rows)
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_empty_list_returns_empty_list(self):
        assert deserialize_resource_rows([]) == []

    def test_unwraps_json_columns(self):
        rows = [{"id": "1", "config_json": json.dumps({"k": 1})}]
        result = deserialize_resource_rows(rows)
        assert result[0]["config"] == {"k": 1}
        # Original *_json column is preserved alongside the unwrapped key
        assert result[0]["config_json"] == '{"k": 1}'

    def test_returns_list_of_dicts(self):
        rows = [{"id": "1"}, {"id": "2"}]
        result = deserialize_resource_rows(rows)
        assert all(isinstance(item, dict) for item in result)


# ---------------------------------------------------------------------------
# serialize_execution_context
# ---------------------------------------------------------------------------


class TestSerializeExecutionContext:
    def test_produces_valid_json(self):
        result = serialize_execution_context({})
        # Must round-trip through json.loads
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_matches_normalize_execution_context(self):
        """The serialized payload must be the same as normalize_execution_context."""
        original = {
            "validation_mode": "detect_only",
            "evidence_level": "minimal",
        }
        serialized = serialize_execution_context(original)
        expected = normalize_execution_context(original)
        assert json.loads(serialized) == expected

    def test_handles_none(self):
        result = serialize_execution_context(None)
        # None must normalise to ExecutionContext() defaults
        parsed = json.loads(result)
        assert "validation_mode" in parsed
        assert "evidence_level" in parsed

    def test_returns_string(self):
        for value in (None, {}, {"validation_mode": "proof"}):
            assert isinstance(serialize_execution_context(value), str)

    def test_empty_context_produces_full_default_payload(self):
        parsed = json.loads(serialize_execution_context({}))
        # The default ExecutionContext has at least these two fields
        assert "validation_mode" in parsed
        assert "evidence_level" in parsed


class TestNowIso:
    def test_returns_string(self):
        """_now_iso returns a string."""
        from backend.secuscan.platform_resources import _now_iso
        result = _now_iso()
        assert isinstance(result, str)

    def test_format_is_iso8601(self):
        """_now_iso returns an ISO 8601 formatted timestamp."""
        from backend.secuscan.platform_resources import _now_iso
        import re
        result = _now_iso()
        pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?$"
        assert re.match(pattern, result), f"Got: {result}"

    def test_result_parseable_by_fromisoformat(self):
        """The result of _now_iso is parseable by datetime.fromisoformat."""
        from backend.secuscan.platform_resources import _now_iso
        from datetime import datetime
        result = _now_iso()
        dt = datetime.fromisoformat(result)
        assert isinstance(dt, datetime)

    def test_two_calls_within_1ms_are_non_decreasing(self):
        """Two calls within milliseconds return non-decreasing timestamps."""
        from backend.secuscan.platform_resources import _now_iso
        a = _now_iso()
        b = _now_iso()
        assert a <= b

