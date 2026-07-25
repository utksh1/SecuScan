"""Tests for UTC timestamp helpers and report timezone standardization."""

from datetime import datetime, timezone, timedelta

import pytest

from backend.secuscan.time_utils import (
    ensure_utc,
    format_utc_display,
    parse_to_utc,
    to_utc_iso,
    utc_now,
)
from backend.secuscan.reporting import ReportGenerator
from backend.secuscan.executor import _parse_discovered_at
from backend.secuscan.routes_json_helpers import deserialize_finding_rows


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_ensure_utc_treats_naive_as_utc():
    naive = datetime(2026, 7, 15, 12, 0, 0)
    aware = ensure_utc(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.hour == 12


def test_ensure_utc_converts_other_offsets():
    eastern = datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone(timedelta(hours=-4)))
    utc_value = ensure_utc(eastern)
    assert utc_value.hour == 12
    assert utc_value.tzinfo == timezone.utc


@pytest.mark.parametrize(
    "raw,expected_hour",
    [
        ("2026-07-15T12:00:00Z", 12),
        ("2026-07-15T12:00:00+00:00", 12),
        ("2026-07-15 12:00:00", 12),
        ("2026-07-15T08:00:00-04:00", 12),
    ],
)
def test_parse_to_utc_handles_common_formats(raw, expected_hour):
    parsed = parse_to_utc(raw)
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    assert parsed.hour == expected_hour


def test_to_utc_iso_includes_offset():
    iso = to_utc_iso("2026-07-15T12:00:00")
    assert iso.endswith("+00:00") or iso.endswith("Z")
    assert "2026-07-15T12:00:00" in iso.replace("+00:00", "").replace("Z", "")


def test_to_utc_iso_current_time_has_offset():
    iso = to_utc_iso()
    parsed = parse_to_utc(iso)
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc


def test_format_utc_display_uses_utc_label():
    assert format_utc_display("2026-07-15T12:30:00Z") == "Jul 15, 2026 12:30 UTC"
    assert format_utc_display("") == "Unknown"
    assert format_utc_display(None) == "Unknown"


def test_report_payload_generated_at_is_utc_iso():
    task = {
        "id": "task-1",
        "tool_name": "nmap",
        "target": "example.com",
        "status": "completed",
        "created_at": "2026-07-15 10:00:00",
        "preset": "quick",
        "command_used": "nmap example.com",
        "inputs": {},
    }
    result = {
        "findings": [
            {
                "title": "Open port",
                "severity": "info",
                "discovered_at": "2026-07-15T09:00:00",
            }
        ],
        "structured": {},
        "summary": [],
        "errors": [],
    }
    payload = ReportGenerator._build_report_payload(task, result)

    generated = parse_to_utc(payload["generated_at"])
    assert generated is not None
    assert generated.tzinfo == timezone.utc
    assert "+" in payload["generated_at"] or payload["generated_at"].endswith("Z")

    created = parse_to_utc(payload["created_at"])
    assert created is not None
    assert created.hour == 10

    finding = payload["findings"][0]
    discovered = parse_to_utc(finding["discovered_at"])
    assert discovered is not None
    assert discovered.hour == 9
    assert finding["discovered_at"].endswith("+00:00") or finding["discovered_at"].endswith("Z")


def test_report_format_timestamp_is_utc_display():
    assert ReportGenerator._format_timestamp("2026-07-15T12:30:00Z") == "Jul 15, 2026 12:30 UTC"
    assert ReportGenerator._format_timestamp("2026-07-15 12:30:00") == "Jul 15, 2026 12:30 UTC"


def test_parse_discovered_at_returns_aware_utc():
    naive = _parse_discovered_at({"discovered_at": "2026-07-15T12:00:00"})
    assert naive.tzinfo == timezone.utc

    offset = _parse_discovered_at({"discovered_at": "2026-07-15T08:00:00-04:00"})
    assert offset.tzinfo == timezone.utc
    assert offset.hour == 12

    missing = _parse_discovered_at({})
    assert missing.tzinfo == timezone.utc


def test_deserialize_finding_rows_normalizes_discovered_at():
    rows = [
        {
            "id": "f1",
            "discovered_at": "2026-07-15 12:00:00",
            "first_seen_at": "2026-07-14T12:00:00Z",
            "last_seen_at": "2026-07-15T12:00:00+00:00",
            "metadata_json": "{}",
        }
    ]
    findings = deserialize_finding_rows(rows)
    assert findings[0]["discovered_at"].endswith("+00:00") or findings[0]["discovered_at"].endswith("Z")
    assert findings[0]["first_seen_at"].endswith("+00:00") or findings[0]["first_seen_at"].endswith("Z")
    assert parse_to_utc(findings[0]["discovered_at"]).hour == 12
