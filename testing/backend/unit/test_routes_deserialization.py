"""
Unit tests for routes JSON deserialization helpers.

Imports the real production functions from backend.secuscan.routes_json_helpers
so a regression in the actual implementation is caught by these tests.
"""

import json

from backend.secuscan.routes_json_helpers import (
    FINDING_JSON_FIELDS,
    deserialize_asset_service_rows,
    deserialize_finding_rows,
    parse_json_fields,
)


# parse_json_fields


def test_parse_json_fields_parses_valid_json_string():
    rows = [{"id": 1, "metadata_json": '{"key": "value"}'}]
    result = parse_json_fields(rows, ["metadata_json"])
    assert result[0]["metadata_json"] == {"key": "value"}


def test_parse_json_fields_preserves_non_json_fields():
    rows = [{"id": 1, "name": "test", "data_json": '{"x": 1}'}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["id"] == 1
    assert result[0]["name"] == "test"
    assert result[0]["data_json"] == {"x": 1}


def test_parse_json_fields_invalid_json_string():
    rows = [{"id": 1, "data_json": "not valid json{"}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] == "not valid json{"


def test_parse_json_fields_already_parsed_dict():
    rows = [{"id": 1, "data_json": {"already": "parsed"}}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] == {"already": "parsed"}


def test_parse_json_fields_empty_rows():
    assert parse_json_fields([], ["metadata_json"]) == []


def test_parse_json_fields_missing_field():
    rows = [{"id": 1, "name": "orphan"}]
    result = parse_json_fields(rows, ["metadata_json"])
    assert result[0]["id"] == 1
    assert "metadata_json" not in result[0]


def test_parse_json_fields_multiple_fields():
    rows = [{"id": 1, "meta_json": '{"a":1}', "ref_json": '{"b":2}'}]
    result = parse_json_fields(rows, ["meta_json", "ref_json"])
    assert result[0]["meta_json"] == {"a": 1}
    assert result[0]["ref_json"] == {"b": 2}


def test_parse_json_fields_null_field_value():
    rows = [{"id": 1, "data_json": None}, {"id": 2}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] is None
    assert "data_json" not in result[1]


# deserialize_finding_rows


def test_deserialize_finding_rows_renames_all_json_fields():
    row = {
        "id": "f1",
        "metadata_json": '{"severity": "high"}',
        "risk_factors_json": '["owasp"]',
        "evidence_json": '{"screenshot": "http://example.com"}',
        "asset_refs_json": '["asset-1"]',
        "references_json": '["https://ref.com"]',
        "corroborating_sources_json": '["src-a"]',
    }
    result = deserialize_finding_rows([row])
    finding = result[0]

    assert "metadata_json" not in finding
    assert "risk_factors_json" not in finding
    assert "evidence_json" not in finding
    assert "asset_refs_json" not in finding
    assert "references_json" not in finding
    assert "corroborating_sources_json" not in finding

    assert finding["metadata"] == {"severity": "high"}
    assert finding["risk_factors"] == ["owasp"]
    assert finding["evidence"] == {"screenshot": "http://example.com"}
    assert finding["asset_refs"] == ["asset-1"]
    assert finding["references"] == ["https://ref.com"]
    assert finding["corroborating_sources"] == ["src-a"]


def test_deserialize_finding_rows_id_preserved():
    row = {"id": "finding-123", "metadata_json": "{}"}
    result = deserialize_finding_rows([row])
    assert result[0]["id"] == "finding-123"


def test_deserialize_finding_rows_partial_fields():
    row = {"id": "f1", "metadata_json": '{"key": "val"}'}
    result = deserialize_finding_rows([row])
    assert result[0]["metadata"] == {"key": "val"}
    assert "risk_factors" not in result[0]


def test_deserialize_finding_rows_empty_input():
    assert deserialize_finding_rows([]) == []


def test_deserialize_finding_rows_invalid_json_leaves_field():
    # parse_json_fields preserves the raw string on JSONDecodeError, so the
    # renamed metadata key holds the original string.
    row = {"id": "f1", "metadata_json": "not-json"}
    result = deserialize_finding_rows([row])
    assert "metadata_json" not in result[0]
    assert result[0]["metadata"] == "not-json"


# deserialize_asset_service_rows


def test_deserialize_asset_service_rows_renames_both_fields():
    row = {
        "id": "a1",
        "metadata_json": '{"ip": "1.2.3.4"}',
        "cert_san_json": '["host1.local"]',
    }
    result = deserialize_asset_service_rows([row])
    asset = result[0]

    assert "metadata_json" not in asset
    assert "cert_san_json" not in asset
    assert asset["metadata"] == {"ip": "1.2.3.4"}
    assert asset["cert_san"] == ["host1.local"]


def test_deserialize_asset_service_rows_id_preserved():
    row = {"id": "asset-99", "ip_address": "5.6.7.8", "metadata_json": "{}"}
    result = deserialize_asset_service_rows([row])
    assert result[0]["id"] == "asset-99"
    assert result[0]["ip_address"] == "5.6.7.8"


def test_deserialize_asset_service_rows_partial_fields():
    row = {"id": "a1", "metadata_json": '{"port": 443}'}
    result = deserialize_asset_service_rows([row])
    assert result[0]["metadata"] == {"port": 443}
    assert "cert_san" not in result[0]


def test_deserialize_asset_service_rows_empty_input():
    assert deserialize_asset_service_rows([]) == []


def test_deserialize_asset_service_rows_only_metadata():
    row = {"id": "svc-1", "metadata_json": '{"service": "http"}'}
    result = deserialize_asset_service_rows([row])
    assert result[0]["metadata"] == {"service": "http"}
    assert "cert_san" not in result[0]


# FINDING_JSON_FIELDS constant


def test_finding_json_fields_has_expected_keys():
    expected = {
        "metadata_json",
        "risk_factors_json",
        "evidence_json",
        "asset_refs_json",
        "references_json",
        "corroborating_sources_json",
    }
    assert set(FINDING_JSON_FIELDS) == expected
