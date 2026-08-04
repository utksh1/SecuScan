"""
testing/backend/unit/test_finding_export.py

Issue #94 / #1875 — serializer-level tests for the bulk findings export.

The CSV column contract asserted here was previously enforced by the frontend
test for ``serializeFindingsToCSV``. That serializer is gone: the file is built
on the backend now, so the contract has to be pinned on this side or nothing
catches a column being renamed, reordered, or dropped.
"""

import csv
import io
import json

import pytest

from backend.secuscan.finding_export import (
    CSV_COLUMNS,
    export_filename,
    finding_csv_row,
    redacted_finding,
    sanitize_csv_cell,
    stream_csv,
    stream_json,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _batches(*batches):
    for batch in batches:
        yield list(batch)


async def _collect(streamer, *batches) -> str:
    return "".join([chunk async for chunk in streamer(_batches(*batches))])


SAMPLE = {
    "id": "f-1",
    "owner_id": "default",
    "title": "SQL Injection",
    "severity": "critical",
    "category": "Database",
    "target": "http://target1.local",
    "discovered_at": "2026-05-12T10:30:00Z",
    "cvss": 9.8,
    "cve": "CVE-2026-1234",
    "risk_score": 9.5,
    "confidence": 0.9,
    "validated": True,
    "analyst_status": "confirmed",
    "description": "An injection vulnerability in input parameter.",
    "remediation": "Use parameterized queries.",
}


# ---------------------------------------------------------------------------
# CSV column contract
# ---------------------------------------------------------------------------

class TestCsvContract:

    def test_column_order_is_pinned(self):
        assert list(CSV_COLUMNS) == [
            "ID",
            "Title",
            "Severity",
            "Category",
            "Target",
            "Discovered At",
            "CVSS",
            "CVE",
            "Risk Score",
            "Confidence",
            "Validated",
            "Analyst Status",
            "Description",
            "Remediation",
        ]

    def test_row_maps_every_column(self):
        assert finding_csv_row(SAMPLE) == [
            "f-1",
            "SQL Injection",
            "critical",
            "Database",
            "http://target1.local",
            "2026-05-12T10:30:00Z",
            "9.8",
            "CVE-2026-1234",
            "9.5",
            "0.9",
            "true",
            "confirmed",
            "An injection vulnerability in input parameter.",
            "Use parameterized queries.",
        ]

    def test_row_length_matches_header(self):
        assert len(finding_csv_row(SAMPLE)) == len(CSV_COLUMNS)

    def test_missing_values_become_empty_strings(self):
        row = finding_csv_row({"id": "f-2"})
        assert row[0] == "f-2"
        assert row[6] == "", "absent CVSS must be blank, not 'None'"
        assert row[8] == "", "absent risk score must be blank, not 'None'"

    def test_zero_is_not_confused_with_absent(self):
        row = finding_csv_row({"id": "f-3", "cvss": 0, "confidence": 0.0})
        assert row[6] == "0"
        assert row[9] == "0.0"

    def test_unvalidated_finding_renders_false(self):
        assert finding_csv_row({"id": "f-4"})[10] == "false"


# ---------------------------------------------------------------------------
# CSV escaping — commas, quotes and newlines must survive a round trip
# ---------------------------------------------------------------------------

class TestCsvEscaping:

    @pytest.mark.anyio
    async def test_commas_and_quotes_round_trip(self):
        findings = [
            {
                "id": "f-1",
                "title": "Information Disclosure, Version Leak",
                "description": 'Version string "1.2.3" disclosed.',
            }
        ]

        text = await _collect(stream_csv, findings)
        rows = list(csv.reader(io.StringIO(text)))

        assert rows[1][1] == "Information Disclosure, Version Leak"
        assert rows[1][12] == 'Version string "1.2.3" disclosed.'

    @pytest.mark.anyio
    async def test_newline_in_a_field_does_not_break_the_row_count(self):
        findings = [{"id": "f-1", "description": "line one\nline two"}]

        rows = list(csv.reader(io.StringIO(await _collect(stream_csv, findings))))

        assert len(rows) == 2, "an embedded newline leaked into the row structure"
        assert rows[1][12] == "line one\nline two"


# ---------------------------------------------------------------------------
# CSV formula injection (CWE-1236)
# ---------------------------------------------------------------------------
# Findings carry scanner output, so cell content is attacker-influenced. Same
# defence as ReportGenerator._sanitize_csv_cell for the task-report CSV (#2394);
# the two paths must not disagree about what is safe to hand a spreadsheet.

class TestFormulaInjection:

    @pytest.mark.parametrize(
        "payload",
        [
            '=HYPERLINK("http://attacker.example","click")',
            "+cmd|'/C calc'!A0",
            "-2+3",
            "@SUM(A1:A2)",
        ],
    )
    def test_formula_prefixes_are_neutralized(self, payload):
        assert sanitize_csv_cell(payload) == "'" + payload

    def test_ordinary_text_is_untouched(self):
        assert sanitize_csv_cell("Open port 22") == "Open port 22"
        assert sanitize_csv_cell("") == ""
        assert sanitize_csv_cell("9.8") == "9.8"

    def test_every_text_column_is_defended(self):
        """A guard on the title alone would leave eleven other ways in."""
        hostile = "=1+1"
        row = finding_csv_row(
            {
                "id": hostile,
                "title": hostile,
                "severity": hostile,
                "category": hostile,
                "target": hostile,
                "discovered_at": hostile,
                "cve": hostile,
                "analyst_status": hostile,
                "description": hostile,
                "remediation": hostile,
            }
        )
        assert all(cell in ("'=1+1", "", "false") for cell in row), row

    @pytest.mark.anyio
    async def test_payload_survives_as_literal_text_through_the_csv(self):
        payload = '=HYPERLINK("http://attacker.example","click")'
        findings = [{"id": "f-1", "title": payload}]

        text = await _collect(stream_csv, findings)
        rows = list(csv.reader(io.StringIO(text)))

        # Quoted and prefixed: a reader gets the original string back, but a
        # spreadsheet sees text rather than a formula.
        assert rows[1][1] == "'" + payload
        assert not rows[1][1].startswith("=")

    @pytest.mark.anyio
    async def test_json_export_is_not_quote_prefixed(self):
        """The guard is a CSV concern — JSON consumers must get the real value."""
        payload = "=1+1"
        text = await _collect(stream_json, [{"id": "f-1", "title": payload}])
        assert json.loads(text)[0]["title"] == payload


# ---------------------------------------------------------------------------
# Streaming shape
# ---------------------------------------------------------------------------

class TestStreaming:

    @pytest.mark.anyio
    async def test_csv_header_is_emitted_before_any_batch(self):
        chunks = [chunk async for chunk in stream_csv(_batches([SAMPLE]))]
        assert chunks[0].startswith("ID,Title,Severity")

    @pytest.mark.anyio
    async def test_csv_spans_multiple_batches(self):
        text = await _collect(
            stream_csv,
            [{"id": "a"}, {"id": "b"}],
            [{"id": "c"}],
        )
        rows = list(csv.reader(io.StringIO(text)))
        assert [row[0] for row in rows[1:]] == ["a", "b", "c"]

    @pytest.mark.anyio
    async def test_empty_csv_is_header_only(self):
        rows = list(csv.reader(io.StringIO(await _collect(stream_csv))))
        assert rows == [list(CSV_COLUMNS)]

    @pytest.mark.anyio
    async def test_json_spans_multiple_batches(self):
        text = await _collect(stream_json, [{"id": "a"}, {"id": "b"}], [{"id": "c"}])
        assert [f["id"] for f in json.loads(text)] == ["a", "b", "c"]

    @pytest.mark.anyio
    async def test_empty_json_is_an_empty_array(self):
        assert json.loads(await _collect(stream_json)) == []

    @pytest.mark.anyio
    async def test_json_survives_non_serializable_values(self):
        """A stray datetime must not abort a 5000-row export mid-stream."""
        from datetime import datetime

        text = await _collect(stream_json, [{"id": "a", "seen": datetime(2026, 5, 12)}])

        assert json.loads(text)[0]["seen"].startswith("2026-05-12")


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

class TestRedaction:

    def test_secrets_in_free_text_are_scrubbed(self):
        result = redacted_finding(
            {"id": "f-1", "description": "Found AKIAIOSFODNN7EXAMPLE in the bucket policy"}
        )
        assert "AKIAIOSFODNN7EXAMPLE" not in result["description"]
        assert "[REDACTED]" in result["description"]

    def test_metadata_is_redacted(self):
        result = redacted_finding({"id": "f-1", "metadata": {"note": "password=hunter2secret"}})
        assert "hunter2secret" not in json.dumps(result["metadata"])

    def test_owner_id_is_dropped(self):
        assert "owner_id" not in redacted_finding(SAMPLE)

    def test_the_input_finding_is_not_mutated(self):
        original = {"id": "f-1", "description": "Found AKIAIOSFODNN7EXAMPLE here"}
        redacted_finding(original)
        assert original["description"] == "Found AKIAIOSFODNN7EXAMPLE here"

    def test_non_secret_content_is_preserved(self):
        result = redacted_finding(dict(SAMPLE))
        assert result["target"] == "http://target1.local"
        assert result["description"] == SAMPLE["description"]


# ---------------------------------------------------------------------------
# Filenames
# ---------------------------------------------------------------------------

class TestFilenames:

    @pytest.mark.parametrize(
        "export_format,expected",
        [
            ("csv", "secuscan_findings_2026-05-12.csv"),
            ("json", "secuscan_findings_2026-05-12.json"),
            ("sarif", "secuscan_findings_2026-05-12.sarif"),
        ],
    )
    def test_filename_carries_date_and_extension(self, export_format, expected):
        assert export_filename(export_format, "2026-05-12") == expected
