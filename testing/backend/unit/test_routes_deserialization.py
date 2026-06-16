"""
Unit tests for routes.py JSON deserialization helpers.

Copies the test-target functions directly to avoid importing routes.py
(which has async module-level imports that interfere with pytest-asyncio).
"""

import json


# ── Copies of the functions under test (from routes.py) ───────────────────────
# These are frozen copies of the functions as implemented in routes.py.
# Tests verify their actual behavior; refactoring routes.py would require updating these.

FINDING_JSON_FIELDS = [
    "metadata_json",
    "risk_factors_json",
    "evidence_json",
    "asset_refs_json",
    "references_json",
    "corroborating_sources_json",
]


def parse_json_fields(rows, fields):
    """Helper to parse stringified JSON fields from SQLite."""
    parsed = []
    for row in rows:
        item = dict(row)
        for field in fields:
            if item.get(field) and isinstance(item[field], str):
                try:
                    item[field] = json.loads(item[field])
                except json.JSONDecodeError:
                    pass
        parsed.append(item)
    return parsed


def deserialize_finding_rows(rows):
    findings = parse_json_fields(rows, FINDING_JSON_FIELDS)
    for finding in findings:
        if "metadata_json" in finding:
            finding["metadata"] = finding.pop("metadata_json")
        if "risk_factors_json" in finding:
            finding["risk_factors"] = finding.pop("risk_factors_json")
        if "evidence_json" in finding:
            finding["evidence"] = finding.pop("evidence_json")
        if "asset_refs_json" in finding:
            finding["asset_refs"] = finding.pop("asset_refs_json")
        if "references_json" in finding:
            finding["references"] = finding.pop("references_json")
        if "corroborating_sources_json" in finding:
            finding["corroborating_sources"] = finding.pop("corroborating_sources_json")
    return findings


def deserialize_asset_service_rows(rows):
    items = parse_json_fields(rows, ["metadata_json", "cert_san_json"])
    for item in items:
        if "metadata_json" in item:
            item["metadata"] = item.pop("metadata_json")
        if "cert_san_json" in item:
            item["cert_san"] = item.pop("cert_san_json")
    return items


# ── Tests for parse_json_fields ────────────────────────────────────────────────


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
    """Null value in field is left unchanged; missing field is absent from result."""
    rows = [{"id": 1, "data_json": None}, {"id": 2}]
    result = parse_json_fields(rows, ["data_json"])
    assert result[0]["data_json"] is None  # null value preserved
    assert "data_json" not in result[1]   # missing field absent


# ── Tests for deserialize_finding_rows ───────────────────────────────────────


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


def test_deserialize_finding_rows_empty_input():
    """Empty list returns empty list."""
    assert deserialize_finding_rows([]) == []


def test_deserialize_finding_rows_invalid_json_leaves_field():
    """Invalid JSON is left as-is by parse_json_fields.
    deserialize_finding_rows then renames the _json field,
    so metadata_json is gone and metadata holds the raw string.
    """
    row = {"id": "f1", "metadata_json": "not-json"}
    result = deserialize_finding_rows([row])
    assert "metadata_json" not in result[0]
    assert result[0]["metadata"] == "not-json"


# ── Tests for deserialize_asset_service_rows ───────────────────────────────────


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


# ── Tests for FINDING_JSON_FIELDS constant ─────────────────────────────────────


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
