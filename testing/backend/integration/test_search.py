import sqlite3
import uuid

from backend.secuscan.config import settings


def _insert_finding(owner_id="default", title="SQL Injection in login form", description="", category="Injection", severity="high", target="example.com"):
    finding_id = str(uuid.uuid4())
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            """
            INSERT INTO findings (
                id, owner_id, task_id, plugin_id, title, category, severity,
                target, description, remediation
            ) VALUES (?, ?, NULL, 'test_plugin', ?, ?, ?, ?, ?, '')
            """,
            (finding_id, owner_id, title, category, severity, target, description),
        )
        conn.commit()
    return finding_id


def _insert_report(owner_id="default", name="Q3 Security Report", report_type="technical"):
    report_id = str(uuid.uuid4())
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute(
            """
            INSERT INTO reports (id, owner_id, task_id, name, type)
            VALUES (?, ?, NULL, ?, ?)
            """,
            (report_id, owner_id, name, report_type),
        )
        conn.commit()
    return report_id


def test_search_requires_query_param(test_client):
    """A missing 'q' parameter should be rejected with 422."""
    response = test_client.get("/api/v1/search")
    assert response.status_code == 422


def test_search_finds_matching_finding_by_title(test_client):
    """Search should return findings whose title matches the query."""
    finding_id = _insert_finding(title="SQL Injection in login form")
    _insert_finding(title="Unrelated XSS issue")

    response = test_client.get("/api/v1/search", params={"q": "SQL Injection"})
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "SQL Injection"
    matched_ids = [f["id"] for f in data["findings"]]
    assert finding_id in matched_ids
    assert data["total"] >= 1


def test_search_finds_matching_finding_by_description(test_client):
    """Search should also match against the finding description."""
    finding_id = _insert_finding(
        title="Generic Finding",
        description="A reflected cross-site scripting vulnerability was found",
    )

    response = test_client.get("/api/v1/search", params={"q": "cross-site scripting"})
    assert response.status_code == 200
    data = response.json()

    matched_ids = [f["id"] for f in data["findings"]]
    assert finding_id in matched_ids


def test_search_finds_matching_report_by_name(test_client):
    """Search should return reports whose name matches the query."""
    report_id = _insert_report(name="Quarterly Pentest Summary")
    _insert_report(name="Unrelated Report")

    response = test_client.get("/api/v1/search", params={"q": "Pentest"})
    assert response.status_code == 200
    data = response.json()

    matched_ids = [r["id"] for r in data["reports"]]
    assert report_id in matched_ids


def test_search_is_case_insensitive(test_client):
    """SQLite LIKE is case-insensitive for ASCII by default; verify that holds here."""
    finding_id = _insert_finding(title="Broken Access Control")

    response = test_client.get("/api/v1/search", params={"q": "broken access"})
    assert response.status_code == 200
    matched_ids = [f["id"] for f in response.json()["findings"]]
    assert finding_id in matched_ids


def test_search_returns_empty_for_no_matches(test_client):
    """A query matching nothing should return empty lists, not an error."""
    response = test_client.get("/api/v1/search", params={"q": "zzz_no_such_finding_zzz"})
    assert response.status_code == 200
    data = response.json()
    assert data["findings"] == []
    assert data["reports"] == []
    assert data["total"] == 0


def test_search_escapes_like_wildcards(test_client):
    """A literal '%' or '_' in the query must not act as a SQL wildcard."""
    # This finding's title contains no literal percent sign, so a query of
    # '%' should NOT match it if wildcards are properly escaped.
    _insert_finding(title="Normal finding without special characters")

    response = test_client.get("/api/v1/search", params={"q": "%"})
    assert response.status_code == 200
    data = response.json()
    assert data["findings"] == []
    assert data["reports"] == []


def test_search_respects_limit_param(test_client):
    """The limit parameter should cap the number of results per category."""
    for i in range(5):
        _insert_finding(title=f"Duplicate Match Finding {i}")

    response = test_client.get("/api/v1/search", params={"q": "Duplicate Match", "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["findings"]) <= 2


def test_search_rejects_limit_out_of_range(test_client):
    """limit must stay within the declared 1-100 bounds."""
    response = test_client.get("/api/v1/search", params={"q": "test", "limit": 0})
    assert response.status_code == 422

    response = test_client.get("/api/v1/search", params={"q": "test", "limit": 101})
    assert response.status_code == 422


def test_search_scopes_results_to_owner(test_client):
    """A finding belonging to a different owner must never appear in results (issue #401 pattern)."""
    other_owner_finding_id = _insert_finding(
        owner_id="other_owner",
        title="Owner Isolation Test Finding",
    )

    response = test_client.get("/api/v1/search", params={"q": "Owner Isolation"})
    assert response.status_code == 200
    matched_ids = [f["id"] for f in response.json()["findings"]]
    assert other_owner_finding_id not in matched_ids