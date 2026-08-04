"""
testing/backend/integration/test_findings_export.py

Issue #94 / #1875 — bulk-export findings across all pages, not just the ones
the browser has loaded.

The export used to be assembled client-side from React state, so it could only
ever contain findings already fetched. These tests pin the backend endpoint
that replaces it:

  * selection is sent as ids and resolved against the database
  * an omitted selection means "everything the caller owns"
  * an *empty* selection means nothing — never everything
  * owner scoping, redaction, and the request cap hold
  * an export larger than one database batch comes out whole
"""

import csv
import io
import json
import sqlite3
import uuid

import pytest

from backend.secuscan.config import settings
from backend.secuscan.finding_export import CSV_COLUMNS

ENDPOINT = "/api/v1/findings/export"


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------

def _seed_task(task_id: str) -> None:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, "
            "status, inputs_json, structured_json, consent_granted) "
            "VALUES (?, 'default', 'nmap', 'nmap', '127.0.0.1', "
            "'completed', '{}', '{\"findings\": []}', 1)",
            (task_id,),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_finding(
    finding_id: str,
    task_id: str,
    *,
    owner_id: str = "default",
    title: str = "Test finding",
    severity: str = "low",
    description: str = "desc",
    discovered_at: str = "2026-07-01 12:00:00",
) -> str:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category, "
            "severity, target, description, remediation, discovered_at) "
            "VALUES (?, ?, ?, 'nmap', ?, 'network', ?, '127.0.0.1', ?, 'fix', ?)",
            (finding_id, owner_id, task_id, title, severity, description, discovered_at),
        )
        conn.commit()
    finally:
        conn.close()
    return finding_id


@pytest.fixture
def seeded_task(test_client):
    """A completed task the seeded findings can hang off."""
    task_id = str(uuid.uuid4())
    _seed_task(task_id)
    return task_id


def export(client, **body):
    return client.post(ENDPOINT, json=body)


def csv_rows(response) -> list:
    return list(csv.reader(io.StringIO(response.text)))


# ---------------------------------------------------------------------------
# 1. Selection is resolved server-side
# ---------------------------------------------------------------------------

class TestSelectionResolution:

    def test_selected_ids_are_exported(self, test_client, seeded_task):
        wanted = _seed_finding("f-wanted", seeded_task, title="Wanted")
        _seed_finding("f-other", seeded_task, title="Other")

        r = export(test_client, finding_ids=[wanted], format="csv")

        assert r.status_code == 200
        rows = csv_rows(r)
        assert rows[0] == list(CSV_COLUMNS)
        assert len(rows) == 2
        assert rows[1][0] == "f-wanted"

    def test_omitted_selection_exports_everything_owned(self, test_client, seeded_task):
        for i in range(4):
            _seed_finding(f"f-{i}", seeded_task)

        r = export(test_client, format="csv")

        assert r.status_code == 200
        assert len(csv_rows(r)) == 5  # header + 4

    def test_empty_selection_exports_nothing(self, test_client, seeded_task):
        """An empty selection must never be read as 'export everything'."""
        for i in range(3):
            _seed_finding(f"f-{i}", seeded_task)

        r = export(test_client, finding_ids=[], format="csv")

        assert r.status_code == 200
        rows = csv_rows(r)
        assert rows[0] == list(CSV_COLUMNS)
        assert len(rows) == 1, f"empty selection exported {len(rows) - 1} findings"

    def test_empty_export_is_still_a_valid_csv(self, test_client, seeded_task):
        r = export(test_client, finding_ids=[], format="csv")
        assert r.status_code == 200
        assert csv_rows(r)[0] == list(CSV_COLUMNS)

    def test_unknown_ids_are_skipped_not_rejected(self, test_client, seeded_task):
        known = _seed_finding("f-known", seeded_task)

        r = export(test_client, finding_ids=[known, "does-not-exist"], format="csv")

        assert r.status_code == 200
        rows = csv_rows(r)
        assert len(rows) == 2
        assert rows[1][0] == "f-known"

    def test_duplicate_ids_do_not_duplicate_rows(self, test_client, seeded_task):
        """Contract guard: a repeated id must not repeat in the file.

        `IN (?, ?, ?)` already collapses duplicates, so this passes without the
        explicit de-duplication too — it is here to catch a future rewrite that
        resolves ids one query at a time.
        """
        known = _seed_finding("f-known", seeded_task)

        r = export(test_client, finding_ids=[known, known, known], format="csv")

        assert r.status_code == 200
        assert len(csv_rows(r)) == 2

    def test_duplicate_ids_are_collapsed_before_the_cap_is_applied(
        self, test_client, seeded_task, monkeypatch
    ):
        """Repeats must not consume the request budget — one id is one finding."""
        monkeypatch.setattr(settings, "max_export_findings", 5)
        known = _seed_finding("f-known", seeded_task)

        r = export(test_client, finding_ids=[known] * 20, format="csv")

        assert r.status_code == 200, "duplicates were counted against the export cap"
        assert len(csv_rows(r)) == 2


# ---------------------------------------------------------------------------
# 2. Owner scoping
# ---------------------------------------------------------------------------

class TestOwnerScoping:

    def test_another_owners_finding_is_not_exported(self, test_client, seeded_task):
        _seed_finding("f-theirs", seeded_task, owner_id="someone-else", title="Theirs")

        r = export(test_client, finding_ids=["f-theirs"], format="csv")

        assert r.status_code == 200
        assert len(csv_rows(r)) == 1, "exported a finding belonging to another owner"

    def test_export_all_excludes_other_owners(self, test_client, seeded_task):
        _seed_finding("f-mine", seeded_task)
        _seed_finding("f-theirs", seeded_task, owner_id="someone-else")

        r = export(test_client, format="csv")

        assert r.status_code == 200
        rows = csv_rows(r)
        assert [row[0] for row in rows[1:]] == ["f-mine"]

    def test_count_header_does_not_confirm_foreign_ids(self, test_client, seeded_task):
        """The reported count must not reveal that a foreign id exists."""
        _seed_finding("f-theirs", seeded_task, owner_id="someone-else")

        r = export(test_client, finding_ids=["f-theirs"], format="csv")

        assert r.headers["X-Export-Finding-Count"] == "0"


# ---------------------------------------------------------------------------
# 3. Formats
# ---------------------------------------------------------------------------

class TestFormats:

    def test_csv_header_matches_declared_columns(self, test_client, seeded_task):
        _seed_finding("f-1", seeded_task)
        r = export(test_client, format="csv")
        assert csv_rows(r)[0] == list(CSV_COLUMNS)
        assert r.headers["content-type"].startswith("text/csv")

    def test_json_export_is_an_array_of_findings(self, test_client, seeded_task):
        _seed_finding("f-1", seeded_task, title="First")
        _seed_finding("f-2", seeded_task, title="Second")

        r = export(test_client, format="json")

        assert r.status_code == 200
        payload = json.loads(r.text)
        assert isinstance(payload, list)
        assert {f["id"] for f in payload} == {"f-1", "f-2"}
        assert {f["title"] for f in payload} == {"First", "Second"}

    def test_empty_json_export_parses_as_empty_array(self, test_client, seeded_task):
        r = export(test_client, finding_ids=[], format="json")
        assert json.loads(r.text) == []

    def test_json_export_omits_owner_id(self, test_client, seeded_task):
        _seed_finding("f-1", seeded_task)
        r = export(test_client, format="json")
        assert all("owner_id" not in f for f in json.loads(r.text))

    def test_sarif_export_is_valid_sarif(self, test_client, seeded_task):
        _seed_finding("f-1", seeded_task, title="Open port 22")

        r = export(test_client, format="sarif")

        assert r.status_code == 200
        payload = json.loads(r.text)
        assert payload["version"] == "2.1.0"
        assert len(payload["runs"]) == 1
        assert len(payload["runs"][0]["results"]) == 1

    def test_unknown_format_is_rejected(self, test_client, seeded_task):
        r = export(test_client, format="xlsx")
        assert r.status_code == 422

    @pytest.mark.parametrize(
        "export_format,extension",
        [("csv", "csv"), ("json", "json"), ("sarif", "sarif")],
    )
    def test_filename_extension_matches_format(
        self, test_client, seeded_task, export_format, extension
    ):
        r = export(test_client, format=export_format)
        disposition = r.headers["content-disposition"]
        assert disposition.startswith("attachment;")
        assert disposition.endswith(f'.{extension}"')


# ---------------------------------------------------------------------------
# 4. Redaction
# ---------------------------------------------------------------------------

class TestRedaction:

    def test_secrets_in_description_are_redacted_in_csv(self, test_client, seeded_task):
        _seed_finding(
            "f-secret",
            seeded_task,
            description="Credential found: AKIAIOSFODNN7EXAMPLE in config",
        )

        r = export(test_client, format="csv")

        assert "AKIAIOSFODNN7EXAMPLE" not in r.text
        assert "[REDACTED]" in r.text

    def test_secrets_in_description_are_redacted_in_json(self, test_client, seeded_task):
        _seed_finding(
            "f-secret",
            seeded_task,
            description="password=hunter2secret was accepted",
        )

        r = export(test_client, format="json")

        assert "hunter2secret" not in r.text
        assert "[REDACTED]" in r.text

    def test_secrets_are_redacted_in_sarif(self, test_client, seeded_task):
        _seed_finding(
            "f-secret",
            seeded_task,
            description="Credential found: AKIAIOSFODNN7EXAMPLE in config",
        )

        r = export(test_client, format="sarif")

        assert "AKIAIOSFODNN7EXAMPLE" not in r.text


# ---------------------------------------------------------------------------
# 5. CSV formula injection (CWE-1236)
# ---------------------------------------------------------------------------

class TestFormulaInjection:
    """Same defence #2394 adds to the task-report CSV, for the findings CSV."""

    def test_formula_injection_from_a_scan_is_neutralized(self, test_client, seeded_task):
        """A hostile finding title must reach the CSV as text, not a formula.

        Titles come from scanner output, so this is reachable end to end by
        anything that reflects a page title or a service banner.
        """
        _seed_finding(
            "f-formula",
            seeded_task,
            title='=HYPERLINK("http://attacker.example","click")',
        )

        r = export(test_client, format="csv")

        assert r.status_code == 200
        title_cell = csv_rows(r)[1][1]
        assert title_cell.startswith("'="), f"formula written raw: {title_cell!r}"

    def test_description_is_defended_too(self, test_client, seeded_task):
        _seed_finding("f-desc", seeded_task, description="@SUM(A1:A2)")

        r = export(test_client, format="csv")

        assert csv_rows(r)[1][12] == "'@SUM(A1:A2)"


# ---------------------------------------------------------------------------
# 6. Volume — the acceptance criterion
# ---------------------------------------------------------------------------

class TestLargeExports:

    def test_export_spanning_many_batches_is_complete(self, test_client, seeded_task, monkeypatch):
        """500 selected findings export whole, across several database batches.

        Every finding shares one discovered_at, so batch boundaries land on
        rows the sort cannot tell apart — the case where a missing ordering
        tiebreaker would repeat or drop rows.
        """
        monkeypatch.setattr(settings, "export_batch_size", 40)

        ids = [f"bulk-{i:04d}" for i in range(500)]
        conn = sqlite3.connect(settings.database_path)
        try:
            conn.executemany(
                "INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category, "
                "severity, target, description, remediation, discovered_at) "
                "VALUES (?, 'default', ?, 'nmap', 'Bulk finding', 'network', "
                "'low', '127.0.0.1', 'desc', 'fix', '2026-07-01 12:00:00')",
                [(fid, seeded_task) for fid in ids],
            )
            conn.commit()
        finally:
            conn.close()

        r = export(test_client, finding_ids=ids, format="csv")

        assert r.status_code == 200
        exported = [row[0] for row in csv_rows(r)[1:]]
        assert len(exported) == 500
        assert sorted(exported) == sorted(ids)
        assert r.headers["X-Export-Finding-Count"] == "500"

    def test_export_all_spanning_many_batches_is_complete(
        self, test_client, seeded_task, monkeypatch
    ):
        monkeypatch.setattr(settings, "export_batch_size", 25)

        ids = [f"bulk-{i:04d}" for i in range(120)]
        conn = sqlite3.connect(settings.database_path)
        try:
            conn.executemany(
                "INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category, "
                "severity, target, description, remediation, discovered_at) "
                "VALUES (?, 'default', ?, 'nmap', 'Bulk finding', 'network', "
                "'low', '127.0.0.1', 'desc', 'fix', '2026-07-01 12:00:00')",
                [(fid, seeded_task) for fid in ids],
            )
            conn.commit()
        finally:
            conn.close()

        r = export(test_client, format="csv")

        exported = [row[0] for row in csv_rows(r)[1:]]
        assert sorted(exported) == sorted(ids)


# ---------------------------------------------------------------------------
# 7. Request cap
# ---------------------------------------------------------------------------

class TestExportCap:

    def test_too_many_ids_is_rejected(self, test_client, seeded_task, monkeypatch):
        monkeypatch.setattr(settings, "max_export_findings", 5)

        r = export(test_client, finding_ids=[f"id-{i}" for i in range(6)], format="csv")

        assert r.status_code == 400
        assert "maximum 5" in r.json()["detail"]

    def test_export_all_beyond_cap_is_rejected(self, test_client, seeded_task, monkeypatch):
        monkeypatch.setattr(settings, "max_export_findings", 2)
        for i in range(3):
            _seed_finding(f"f-{i}", seeded_task)

        r = export(test_client, format="csv")

        assert r.status_code == 400
        assert "Select a subset" in r.json()["detail"]

    def test_at_the_cap_is_accepted(self, test_client, seeded_task, monkeypatch):
        monkeypatch.setattr(settings, "max_export_findings", 3)
        for i in range(3):
            _seed_finding(f"f-{i}", seeded_task)

        r = export(test_client, format="csv")

        assert r.status_code == 200
        assert len(csv_rows(r)) == 4


# ---------------------------------------------------------------------------
# 8. Auth
# ---------------------------------------------------------------------------

class TestAuthRequired:

    def test_export_requires_an_api_key(self, test_client, seeded_task):
        r = test_client.post(ENDPOINT, json={"format": "csv"}, headers={"X-Api-Key": ""})
        assert r.status_code in (401, 403)
