"""
Unit tests for backend.secuscan.routes_json_helpers.

Covers:
- parse_json_fields: parses JSON string fields, leaves non-string/non-truthy unchanged
- parse_json_fields: JSON decode errors keep original string value
- parse_json_fields: does not mutate the original rows
- deserialize_finding_rows: strips *_json suffix and renames to friendly keys
- deserialize_finding_rows: rows without any *_json fields pass through unchanged
- deserialize_finding_rows: does not mutate the original rows
- deserialize_asset_service_rows: parses and renames metadata_json and cert_san_json
- deserialize_asset_service_rows: unknown *_json fields are not renamed
"""

import json

import pytest

from backend.secuscan.routes_json_helpers import (
    FINDING_JSON_FIELDS,
    deserialize_asset_service_rows,
    deserialize_finding_rows,
    parse_json_fields,
)


# ---------------------------------------------------------------------------
# parse_json_fields
# ---------------------------------------------------------------------------


class TestParseJsonFields:
    def test_parses_json_string_fields(self):
        """Fields that are JSON-encoded strings are replaced with parsed objects."""
        rows = [{"name": "n1", "config_json": '{"timeout": 30}'}]
        result = parse_json_fields(rows, ["config_json"])
        assert result[0]["config_json"] == {"timeout": 30}

    def test_preserves_non_string_fields(self):
        """Fields that are not strings are passed through."""
        rows = [{"name": "n1", "count": 5, "enabled": True}]
        result = parse_json_fields(rows, ["count", "enabled"])
        assert result[0]["count"] == 5
        assert result[0]["enabled"] is True

    def test_skips_falsy_fields(self):
        """Fields with falsy values (None, empty string) are not parsed."""
        rows = [{"name": "n1", "data": None}, {"name": "n2", "data": ""}]
        result = parse_json_fields(rows, ["data"])
        assert result[0]["data"] is None
        assert result[1]["data"] == ""

    def test_json_decode_error_keeps_original_string(self):
        """A JSON decode error preserves the original string value."""
        rows = [{"name": "n1", "bad_json": "not valid json{"}]
        result = parse_json_fields(rows, ["bad_json"])
        assert result[0]["bad_json"] == "not valid json{"

    def test_parses_multiple_fields_per_row(self):
        """Multiple fields in the same row are all parsed when specified."""
        rows = [{"a": '{"x": 1}', "b": '{"y": 2}', "c": "plain"}]
        result = parse_json_fields(rows, ["a", "b"])
        assert result[0]["a"] == {"x": 1}
        assert result[0]["b"] == {"y": 2}
        assert result[0]["c"] == "plain"

    def test_does_not_mutate_input_rows(self):
        """parse_json_fields must not modify the input list or its dicts."""
        original = [{"config_json": '{"timeout": 30}'}]
        snapshot = json.dumps(original)
        parse_json_fields(original, ["config_json"])
        assert json.dumps(original) == snapshot


# ---------------------------------------------------------------------------
# deserialize_finding_rows
# ---------------------------------------------------------------------------


class TestDeserializeFindingRows:
    def test_strips_json_suffix_and_renames(self):
        """Each *_json field is parsed and renamed to the base name."""
        rows = [
            {
                "id": "f1",
                "metadata_json": '{"severity": "high"}',
                "evidence_json": '["url1", "url2"]',
            }
        ]
        result = deserialize_finding_rows(rows)
        assert "metadata" in result[0]
        assert "metadata_json" not in result[0]
        assert result[0]["metadata"] == {"severity": "high"}
        assert result[0]["evidence"] == ["url1", "url2"]

    def test_rows_without_json_fields_pass_through(self):
        """Rows that have no *_json fields are returned unchanged (renamed to nothing)."""
        rows = [{"id": "f1", "title": "SQL Injection", "severity": "high"}]
        result = deserialize_finding_rows(rows)
        assert result[0]["id"] == "f1"
        assert result[0]["title"] == "SQL Injection"
        assert "metadata" not in result[0]

    def test_partial_json_fields_only_rename_present_keys(self):
        """Only the *_json keys that are present get renamed."""
        rows = [{"id": "f1", "risk_factors_json": '[1, 2, 3]'}]
        result = deserialize_finding_rows(rows)
        assert result[0]["risk_factors"] == [1, 2, 3]
        assert "evidence" not in result[0]
        assert "references" not in result[0]

    def test_does_not_mutate_input_rows(self):
        """deserialize_finding_rows must not modify the input."""
        original = [{"id": "f1", "metadata_json": '{"x": 1}'}]
        snapshot_keys = set(original[0].keys())
        deserialize_finding_rows(original)
        assert set(original[0].keys()) == snapshot_keys


# ---------------------------------------------------------------------------
# deserialize_asset_service_rows
# ---------------------------------------------------------------------------


class TestDeserializeAssetServiceRows:
    def test_parses_and_renames_metadata_and_cert_san(self):
        """metadata_json -> metadata and cert_san_json -> cert_san."""
        rows = [
            {
                "id": "svc1",
                "metadata_json": '{"port": 443}',
                "cert_san_json": '["host1.example.com"]',
            }
        ]
        result = deserialize_asset_service_rows(rows)
        assert result[0]["metadata"] == {"port": 443}
        assert "metadata_json" not in result[0]
        assert result[0]["cert_san"] == ["host1.example.com"]
        assert "cert_san_json" not in result[0]

    def test_ignores_unknown_json_fields(self):
        """Fields not in the target set are left alone."""
        rows = [{"id": "svc1", "extra_json": '{"useless": true}'}]
        result = deserialize_asset_service_rows(rows)
        assert "extra_json" in result[0]
        assert "metadata" not in result[0]

    def test_does_not_mutate_input_rows(self):
        """deserialize_asset_service_rows must not modify the input."""
        original = [{"id": "svc1", "metadata_json": '{"x": 1}'}]
        snapshot_keys = set(original[0].keys())
        deserialize_asset_service_rows(original)
        assert set(original[0].keys()) == snapshot_keys


# ---------------------------------------------------------------------------
# FINDING_JSON_FIELDS
# ---------------------------------------------------------------------------


class TestFindingJsonFields:
    def test_contains_expected_field_names(self):
        """FINDING_JSON_FIELDS lists all the *_json columns used by findings."""
        expected = [
            "metadata_json",
            "risk_factors_json",
            "evidence_json",
            "asset_refs_json",
            "references_json",
            "corroborating_sources_json",
        ]
        assert set(FINDING_JSON_FIELDS) == set(expected)
