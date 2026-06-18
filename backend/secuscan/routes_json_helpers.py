"""
JSON deserialization helpers for SQLite row data — import-safe subset of routes.py.

Contains pure parse/deserialize helpers extracted from routes.py so they can be
unit-tested without pulling in FastAPI, httpx, or the rest of the web layer.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


FINDING_JSON_FIELDS = [
    "metadata_json",
    "risk_factors_json",
    "evidence_json",
    "asset_refs_json",
    "references_json",
    "corroborating_sources_json",
]


def parse_json_fields(rows: List[Dict], fields: List[str]) -> List[Dict]:
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


def deserialize_finding_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
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


def deserialize_asset_service_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
    items = parse_json_fields(rows, ["metadata_json", "cert_san_json"])
    for item in items:
        if "metadata_json" in item:
            item["metadata"] = item.pop("metadata_json")
        if "cert_san_json" in item:
            item["cert_san"] = item.pop("cert_san_json")
    return items
