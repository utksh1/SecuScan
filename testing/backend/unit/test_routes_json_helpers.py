"""
Tests for backend.secuscan.routes_json_helpers pure JSON deserialization helpers.

Covers:
- parse_json_fields: rows with JSON columns, non-string values, invalid JSON
- deserialize_finding_rows: all FINDING_JSON_FIELDS, missing fields, empty list
- deserialize_asset_service_rows: metadata_json and cert_san_json, empty list
"""

from backend.secuscan.routes_json_helpers import (
    parse_json_fields,
    deserialize_finding_rows,
    deserialize_asset_service_rows,
    FINDING_JSON_FIELDS,
)


class TestParseJsonFields:
    def test_parses_string_json_columns(self):
        rows = [
            {"id": "1", "data_json": '{"key": "value"}'},
            {"id": "2", "data_json": '{"other": 42}'},
        ]
        result = parse_json_fields(rows, ["data_json"])
        # parse_json_fields overwrites the _json key with the parsed value
        assert result[0]["data_json"] == {"key": "value"}
        assert result[1]["data_json"] == {"other": 42}

    def test_non_string_values_left_unchanged(self):
        rows = [{"id": "1", "data_json": {"nested": True}}]
        result = parse_json_fields(rows, ["data_json"])
        assert result[0]["data_json"] == {"nested": True}

    def test_invalid_json_left_as_string(self):
        rows = [{"id": "1", "data_json": "not valid json {"}]
        result = parse_json_fields(rows, ["data_json"])
        assert result[0]["data_json"] == "not valid json {"

    def test_missing_field_left_unchanged(self):
        rows = [{"id": "1"}]
        result = parse_json_fields(rows, ["data_json"])
        assert "data_json" not in result[0]


class TestDeserializeFindingRows:
    def test_deserializes_all_finding_json_fields(self):
        rows = [
            {
                "id": "finding-1",
                "metadata_json": '{"cvss": 9.1}',
                "risk_factors_json": '["CVE-2024-1234"]',
                "evidence_json": '[{"type": "screenshot"}]',
                "asset_refs_json": '["asset-1"]',
                "references_json": '[{"url": "http://example.com"}]',
                "corroborating_sources_json": '[{"source": "nmap"}]',
            }
        ]
        results = deserialize_finding_rows(rows)
        assert len(results) == 1
        r = results[0]
        assert r["metadata"] == {"cvss": 9.1}
        assert r["risk_factors"] == ["CVE-2024-1234"]
        assert r["evidence"] == [{"type": "screenshot"}]
        assert r["asset_refs"] == ["asset-1"]
        assert r["references"] == [{"url": "http://example.com"}]
        assert r["corroborating_sources"] == [{"source": "nmap"}]
        # Original _json keys renamed
        assert "metadata_json" not in r

    def test_missing_optional_fields_ignored(self):
        rows = [{"id": "finding-1", "severity": "high"}]
        results = deserialize_finding_rows(rows)
        assert len(results) == 1
        assert results[0]["severity"] == "high"

    def test_empty_rows_list(self):
        results = deserialize_finding_rows([])
        assert results == []

    def test_invalid_json_in_field_preserved_and_renamed(self):
        rows = [{"id": "1", "metadata_json": "broken {"}]
        results = deserialize_finding_rows(rows)
        # parse_json_fields keeps the key on decode failure; then deserialize_finding_rows
        # renames it to "metadata" (regardless of whether the value is valid JSON)
        assert results[0].get("metadata") == "broken {"


class TestDeserializeAssetServiceRows:
    def test_deserializes_metadata_and_cert_san(self):
        rows = [
            {
                "id": "svc-1",
                "metadata_json": '{"port": 443}',
                "cert_san_json": '["example.com", "www.example.com"]',
            }
        ]
        results = deserialize_asset_service_rows(rows)
        assert len(results) == 1
        assert results[0]["metadata"] == {"port": 443}
        assert results[0]["cert_san"] == ["example.com", "www.example.com"]
        assert "metadata_json" not in results[0]
        assert "cert_san_json" not in results[0]

    def test_empty_rows_list(self):
        results = deserialize_asset_service_rows([])
        assert results == []

    def test_missing_fields_handled(self):
        rows = [{"id": "svc-1", "host": "1.2.3.4"}]
        results = deserialize_asset_service_rows(rows)
        assert len(results) == 1
        assert results[0]["host"] == "1.2.3.4"
