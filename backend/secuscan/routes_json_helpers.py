"""
Pure JSON deserialization helpers for routes.py.

These helpers were originally defined inline in routes.py. They were extracted
into this small import-safe module so that they can be unit-tested directly
without pulling in the heavy routes.py import chain (FastAPI, reporting,
xhtml2pdf, etc.). routes.py re-imports them from here so the public API is
unchanged.

The functions are pure: they take rows (dicts) and return new lists of dicts.
They never mutate their inputs.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def parse_json_fields(rows: List[Dict], fields: List[str]) -> List[Dict]:
    """Parse stringified JSON fields from a list of row dicts.

    For each row in *rows*, the named *fields* are checked. If a field is
    present, truthy, and a string, it is parsed with :func:`json.loads`.
    Parsing failures are silently preserved (the original string is kept).

    Args:
        rows:   Iterable of row dicts (typically from a SQL query).
        fields: Column names whose values may be JSON-encoded strings.

    Returns:
        A new list of row dicts with the named fields parsed.
    """
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


FINDING_JSON_FIELDS = [
    "metadata_json",
    "risk_factors_json",
    "evidence_json",
    "asset_refs_json",
    "references_json",
    "corroborating_sources_json",
]


def deserialize_finding_rows(rows: List[Dict]) -> List[Dict[str, Any]]:
    """Parse JSON fields on finding rows and rename them to friendly keys.

    The ``*_json`` suffix is stripped from the parsed values:
    ``metadata_json`` -> ``metadata``, ``evidence_json`` -> ``evidence``, etc.
    Rows that do not contain a given ``*_json`` key are passed through.
    """
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
    """Parse JSON fields on asset-service rows and rename them.

    Only ``metadata_json`` and ``cert_san_json`` are parsed; both are renamed
    to ``metadata`` and ``cert_san`` respectively.
    """
    items = parse_json_fields(rows, ["metadata_json", "cert_san_json"])
    for item in items:
        if "metadata_json" in item:
            item["metadata"] = item.pop("metadata_json")
        if "cert_san_json" in item:
            item["cert_san"] = item.pop("cert_san_json")
    return items
