"""
Unit tests for routes.py JSON deserialization helpers.

Covers: parse_json_fields, deserialize_finding_rows, deserialize_asset_service_rows
"""

import json
from backend.secuscan.routes import (
    parse_json_fields,
    deserialize_finding_rows,
    deserialize_asset_service_rows,
    FINDING_JSON_FIELDS,
)


# ── parse_json_fields ──────────────────────────────────────────────────────────


def test_parse_json_fields_parses_valid_json_string():
    """String JSON field is parsed into a dict."""
    rows = [{"id": 1, "metadata_json": '{"key": "value"}'}]
    result = parse_json_fields(rows, ["metadata_json"])
    assert result[0]["metadata_json"] == {"key": "value"}


def test_parse_json_fields_preserves_non_json_fields():
    """Non-JSON fields are left unchanged."""
    rows = [{"id": 1, "name": "test", "data_json": '{"x": 1}'}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["id"] == 1
    assert result[0]["name"] == "test"
    assert result[0]["data_json"] == {"x": 1}


def test_parse_json_fields_invalid_json_string():
    """Invalid JSON string is left unchanged (not overwritten with None)."""
    rows = [{"id": 1, "data_json": "not valid json{"}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] == "not valid json{"


def test_parse_json_fields_already_parsed_dict():
    """Already-parsed dict field is left unchanged."""
    rows = [{"id": 1, "data_json": {"already": "parsed"}}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] == {"already": "parsed"}


def test_parse_json_fields_empty_rows():
    """Empty list returns empty list."""
    result = parse_json_fields([], ["metadata_json"])
    assert result == []


def test_parse_json_fields_missing_field():
    """Row without the JSON field is returned unchanged."""
    rows = [{"id": 1, "name": "orphan"}]
    result = parse_json_fields(rows, ["metadata_json"])
    assert result[0]["id"] == 1
    assert "metadata_json" not in result[0]


def test_parse_json_fields_multiple_fields():
    """Multiple JSON fields in a single row are all parsed."""
    rows = [{"id": 1, "meta_json": '{"a":1}', "ref_json": '{"b":2}'}]
    result = parse_json_fields(rows, ["meta_json", "ref_json"])
    assert result[0]["meta_json"] == {"a": 1}
    assert result[0]["ref_json"] == {"b": 2}


def test_parse_json_fields_null_field_value():
    """Null/missing field value is skipped (no exception)."""
    rows = [{"id": 1, "data_json": None}, {"id": 2}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] is None
    assert result[1]["data_json"] is None


# ── deserialize_finding_rows ──────────────────────────────────────────────────


def test_deserialize_finding_rows_renames_all_json_fields():
    """All six FINDING_JSON_FIELDS are renamed to their top-level keys."""
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

    # Old keys are gone
    assert "metadata_json" not in finding
    assert "risk_factors_json" not in finding
    assert "evidence_json" not in finding
    assert "asset_refs_json" not in finding
    assert "references_json" not in finding
    assert "corroborating_sources_json" not in finding

    # New keys are present
    assert finding["metadata"] == {"severity": "high"}
    assert finding["risk_factors"] == ["owasp"]
    assert finding["evidence"] == {"screenshot": "http://example.com"}
    assert finding["asset_refs"] == ["asset-1"]
    assert finding["references"] == ["https://ref.com"]
    assert finding["corroborating_sources"] == ["src-a"]


def test_deserialize_finding_rows_id_preserved():
    """Non-JSON fields like 'id' are preserved unchanged."""
    row = {"id": "finding-123", "metadata_json": "{}"}
    result = deserialize_finding_rows([row])
    assert result[0]["id"] == "finding-123"


def test_deserialize_finding_rows_partial_fields():
    """Row missing some JSON fields does not raise KeyError."""
    row = {"id": "f1", "metadata_json": '{"key": "val"}'}
    result = deserialize_finding_rows([row])
    assert result[0]["metadata"] == {"key": "val"}
    assert "risk_factors" not in result[0]


def test_deserialize_finding_rows_no_key_collision():
    """If both 'metadata' and 'metadata_json' exist, the original 'metadata' is preserved."""
    row = {"id": "f1", "metadata": "already-here", "metadata_json": '{"new": "val"}'}
    result = deserialize_finding_rows([row])
    # deserialize_finding_rows does pop() first then sets new key,
    # so the result should have the parsed version
    assert result[0]["metadata"] == {"new": "val"}


def test_deserialize_finding_rows_empty_input():
    """Empty list returns empty list."""
    assert deserialize_finding_rows([]) == []


def test_deserialize_finding_rows_invalid_json_leaves_field():
    """Invalid JSON in a field is left as-is (parse_json_fields skips it)."""
    row = {"id": "f1", "metadata_json": "not-json"}
    result = deserialize_finding_rows([row])
    assert result[0]["metadata_json"] == "not-json"
    assert "metadata" not in result[0]


# ── deserialize_asset_service_rows ───────────────────────────────────────────


def test_deserialize_asset_service_rows_renames_both_fields():
    """metadata_json and cert_san_json are renamed."""
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
    """Non-JSON fields are preserved."""
    row = {"id": "asset-99", "ip_address": "5.6.7.8", "metadata_json": "{}"}
    result = deserialize_asset_service_rows([row])
    assert result[0]["id"] == "asset-99"
    assert result[0]["ip_address"] == "5.6.7.8"


def test_deserialize_asset_service_rows_partial_fields():
    """Row missing cert_san_json does not raise KeyError."""
    row = {"id": "a1", "metadata_json": '{"port": 443}'}
    result = deserialize_asset_service_rows([row])
    assert result[0]["metadata"] == {"port": 443}
    assert "cert_san" not in result[0]


def test_deserialize_asset_service_rows_empty_input():
    """Empty list returns empty list."""
    assert deserialize_asset_service_rows([]) == []


def test_deserialize_asset_service_rows_only_metadata():
    """Asset with only metadata_json is handled correctly."""
    row = {"id": "svc-1", "metadata_json": '{"service": "http"}'}
    result = deserialize_asset_service_rows([row])
    assert result[0]["metadata"] == {"service": "http"}
    assert "cert_san" not in result[0]


# ── FINDING_JSON_FIELDS constant ───────────────────────────────────────────────


def test_finding_json_fields_has_expected_keys():
    """FINDING_JSON_FIELDS contains exactly the six expected field names."""
    expected = {
        "metadata_json",
        "risk_factors_json",
        "evidence_json",
        "asset_refs_json",
        "references_json",
        "corroborating_sources_json",
    }
    assert set(FINDING_JSON_FIELDS) == expected
