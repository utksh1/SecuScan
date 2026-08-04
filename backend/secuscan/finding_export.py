"""
Bulk findings export serializers.

Findings export used to be assembled entirely in the browser from whatever the
user had scrolled into memory, so anything not loaded could not be exported.
These serializers run against rows read straight from the database, which makes
the export independent of the client's page state.

Everything here is chunk-at-a-time on purpose: ``stream_csv`` and
``stream_json`` consume an async iterator of finding batches and yield text as
they go, so the size of an export is bounded by the batch size rather than by
the number of findings. SARIF is the exception and is documented below.

Redaction mirrors :mod:`backend.secuscan.reporting` — the same fields are
scrubbed with the same helpers, so a findings export and a task report never
disagree about what is safe to write out.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any, AsyncIterator, Dict, Iterable, List, Sequence

from .redaction import _redact_value, redact, redact_dict
from .reporting import reporting

EXPORT_FORMATS: tuple[str, ...] = ("csv", "json", "sarif")

MEDIA_TYPES: Dict[str, str] = {
    "csv": "text/csv; charset=utf-8",
    "json": "application/json",
    "sarif": "application/json",
}

FILE_EXTENSIONS: Dict[str, str] = {
    "csv": "csv",
    "json": "json",
    "sarif": "sarif",
}

# Same columns, same order as the browser-side export, so moving the work to
# the backend does not change the shape of the file analysts already script
# against. (Line endings do change: csv writes RFC 4180 CRLF, matching the
# task report export rather than the browser's bare LF.)
CSV_COLUMNS: tuple[str, ...] = (
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
)

# Free-text columns that can carry secrets lifted out of scanner output.
_REDACTED_TEXT_FIELDS: tuple[str, ...] = (
    "target",
    "description",
    "remediation",
    "proof",
    "confidence_reason",
)

# ``owner_id`` is the caller's own identity repeated on every row: constant for
# the whole export and useless inside it.
_EXCLUDED_FIELDS: frozenset[str] = frozenset({"owner_id"})


def redacted_finding(finding: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``finding`` safe to write into an export file."""
    exported = {key: value for key, value in finding.items() if key not in _EXCLUDED_FIELDS}

    for field in _REDACTED_TEXT_FIELDS:
        value = exported.get(field)
        if isinstance(value, str) and value:
            exported[field] = redact(value)

    metadata = exported.get("metadata")
    if isinstance(metadata, dict):
        exported["metadata"] = redact_dict(metadata)

    evidence = exported.get("evidence")
    if isinstance(evidence, list):
        exported["evidence"] = _redact_value(evidence)

    return exported


# Spreadsheet applications evaluate a cell beginning with any of these as a
# formula, so a finding title of ``=HYPERLINK("http://attacker","click")``
# becomes a live link when the export is opened.
_FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@")


def sanitize_csv_cell(value: str) -> str:
    """Neutralize CSV formula injection (CWE-1236).

    Findings carry scanner output — page titles, banners, reflected headers —
    so cell content is attacker-influenced. Prefixing with a single quote makes
    the spreadsheet treat the cell as literal text.

    Deliberately mirrors ``ReportGenerator._sanitize_csv_cell`` in
    :mod:`backend.secuscan.reporting` (added by #2394 for the task-report CSV).
    Both paths write findings to a spreadsheet and must not disagree about what
    is safe; folding them into one helper is a worthwhile follow-up once both
    have landed.
    """
    if value and value[0] in _FORMULA_PREFIXES:
        return "'" + value
    return value


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _number(value: Any) -> str:
    """Render a numeric column, distinguishing 'absent' from 'zero'."""
    if value is None or value == "":
        return ""
    return str(value)


def finding_csv_row(finding: Dict[str, Any]) -> List[str]:
    """Build one CSV row from an already-redacted finding.

    Every cell goes through :func:`sanitize_csv_cell`. The booleans and numeric
    columns cannot start with a formula prefix in valid data, but they are not
    exempted — a column that is only safe while the data is well-formed is not
    a guarantee worth relying on.
    """
    return [
        sanitize_csv_cell(cell)
        for cell in (
            _text(finding.get("id")),
            _text(finding.get("title")),
            _text(finding.get("severity")),
            _text(finding.get("category")),
            _text(finding.get("target")),
            _text(finding.get("discovered_at")),
            _number(finding.get("cvss")),
            _text(finding.get("cve")),
            _number(finding.get("risk_score")),
            _number(finding.get("confidence")),
            "true" if finding.get("validated") else "false",
            _text(finding.get("analyst_status")),
            _text(finding.get("description")),
            _text(finding.get("remediation")),
        )
    ]


def _write_csv_rows(rows: Iterable[Sequence[Any]]) -> str:
    buffer = io.StringIO()
    try:
        # Excel and most CSV readers expect CRLF, which is also what csv writes
        # by default; setting it explicitly keeps the output identical whatever
        # platform the backend runs on.
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerows(rows)
        return buffer.getvalue()
    finally:
        buffer.close()


async def stream_csv(batches: AsyncIterator[List[Dict[str, Any]]]) -> AsyncIterator[str]:
    """Yield a CSV document, one database batch at a time.

    The header is emitted before the first batch is fetched so an export with
    no matching findings is still a valid, openable CSV file.
    """
    yield _write_csv_rows([CSV_COLUMNS])
    async for batch in batches:
        yield _write_csv_rows(finding_csv_row(redacted_finding(f)) for f in batch)


async def stream_json(batches: AsyncIterator[List[Dict[str, Any]]]) -> AsyncIterator[str]:
    """Yield a JSON array of findings, one database batch at a time."""
    yield "["
    first = True
    async for batch in batches:
        for finding in batch:
            yield ("" if first else ",") + json.dumps(redacted_finding(finding), default=str)
            first = False
    yield "]"


async def stream_sarif(batches: AsyncIterator[List[Dict[str, Any]]]) -> AsyncIterator[str]:
    """Yield a SARIF v2.1.0 document.

    Unlike CSV and JSON this cannot stream: SARIF puts the deduplicated ``rules``
    array in the tool driver, ahead of the results that reference it by index,
    so the whole set has to be known before the first byte is correct. The
    batches are still consumed incrementally, but the document is assembled in
    memory — which is why ``max_export_findings`` exists.
    """
    collected: List[Dict[str, Any]] = []
    async for batch in batches:
        collected.extend(redacted_finding(finding) for finding in batch)

    synthetic_task = {
        "id": "findings-export",
        "tool_name": "SecuScan",
        "plugin_id": "secuscan",
        "target": "multiple",
        "status": "completed",
    }
    yield reporting.generate_sarif_report(synthetic_task, {"findings": collected})


STREAMERS = {
    "csv": stream_csv,
    "json": stream_json,
    "sarif": stream_sarif,
}


def export_filename(export_format: str, generated_on: str) -> str:
    """Build the download filename, matching what the browser export used."""
    return f"secuscan_findings_{generated_on}.{FILE_EXTENSIONS[export_format]}"
