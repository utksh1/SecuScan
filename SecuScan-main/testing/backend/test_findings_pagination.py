"""
Tests for pagination metadata in findings list and finding-groups endpoints.
"""

import sqlite3
import uuid

import pytest
from backend.secuscan.config import settings


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


def _seed_finding(finding_id: str, task_id: str, group_id: str, severity: str = "low") -> None:
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category, "
            "severity, target, description, remediation, finding_group_id) "
            "VALUES (?, 'default', ?, 'nmap', 'Test finding', 'network', "
            "?, '127.0.0.1', 'desc', 'fix', ?)",
            (finding_id, task_id, severity, group_id),
        )
        conn.commit()
    finally:
        conn.close()


class TestFindingsPagination:
    """Test pagination metadata for /api/v1/findings endpoint"""

    def test_findings_response_includes_pagination(self, test_client):
        """Response must include pagination metadata."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        _seed_finding(str(uuid.uuid4()), tid, "group:a")

        resp = test_client.get("/api/v1/findings")

        assert resp.status_code == 200
        data = resp.json()
        assert "findings" in data
        assert "finding_groups" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert data["page"] == 1
        assert data["per_page"] == 50

    def test_findings_default_pagination_values(self, test_client):
        """Test default page=1, per_page=50"""
        resp = test_client.get("/api/v1/findings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["per_page"] == 50

    def test_findings_custom_per_page(self, test_client):
        """Test that per_page parameter is respected"""
        resp = test_client.get("/api/v1/findings?page=1&per_page=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["per_page"] == 10

    @pytest.mark.parametrize(
        "qs",
        [
            "page=0",
            "page=-1",
            "per_page=0",
            "per_page=-5",
            "per_page=201",
        ],
    )
    def test_invalid_pagination_is_rejected(self, test_client, qs):
        resp = test_client.get(f"/api/v1/findings?{qs}")
        assert resp.status_code == 422

    def test_finding_groups_are_from_all_findings_not_just_page(self, test_client):
        """Finding groups must be computed from ALL findings, not just the current page.

        Regression test: if groups are built from paginated data, the second
        group would be missing when per_page=1 and only the first finding is
        returned.
        """
        tid = str(uuid.uuid4())
        _seed_task(tid)
        _seed_finding("finding-page1", tid, "group:alpha", "low")
        _seed_finding("finding-page2", tid, "group:beta", "high")

        resp = test_client.get("/api/v1/findings?page=1&per_page=1")

        assert resp.status_code == 200
        data = resp.json()
        # Only 1 finding on this page
        assert len(data["findings"]) == 1
        assert data["findings"][0]["id"] == "finding-page1"
        # But both groups must be present
        group_ids = {g["id"] for g in data["finding_groups"]}
        assert group_ids == {"group:alpha", "group:beta"}, (
            "finding_groups should contain groups from ALL findings, "
            "not just the current page"
        )

    def test_finding_groups_are_identical_across_pages(self, test_client):
        """Cross-page consistency: every page returns the same groups."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        for i in range(5):
            _seed_finding(f"finding-{i}", tid, f"group:{'even' if i % 2 == 0 else 'odd'}")

        page1 = test_client.get("/api/v1/findings?page=1&per_page=2").json()
        page2 = test_client.get("/api/v1/findings?page=2&per_page=2").json()

        groups_p1 = {g["id"] for g in page1["finding_groups"]}
        groups_p2 = {g["id"] for g in page2["finding_groups"]}
        assert groups_p1 == groups_p2, "finding_groups must be identical across pages"

    def test_findings_total_counts_all_findings(self, test_client):
        """Total reflects all findings, not just the page."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        for i in range(7):
            _seed_finding(str(uuid.uuid4()), tid, "group:a")

        resp = test_client.get("/api/v1/findings?page=1&per_page=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert len(data["findings"]) == 3


class TestFindingGroupsPagination:
    """Test /api/v1/finding-groups endpoint returns groups from all findings"""

    def test_finding_groups_returns_all_groups(self, test_client):
        """Groups must always be computed from ALL findings."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        _seed_finding(str(uuid.uuid4()), tid, "group:xss")
        _seed_finding(str(uuid.uuid4()), tid, "group:sqli")

        resp = test_client.get("/api/v1/finding-groups")

        assert resp.status_code == 200
        data = resp.json()
        group_ids = {g["id"] for g in data["groups"]}
        assert group_ids == {"group:xss", "group:sqli"}

    def test_finding_groups_total_matches_all_findings(self, test_client):
        """Total must reflect ALL findings, not a paginated subset."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        for i in range(7):
            _seed_finding(str(uuid.uuid4()), tid, f"group:{i}")

        resp = test_client.get("/api/v1/finding-groups")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7

    def test_finding_groups_pagination_params_do_not_affect_groups(self, test_client):
        """page/per_page query params should not change the returned groups."""
        tid = str(uuid.uuid4())
        _seed_task(tid)
        for i in range(10):
            _seed_finding(str(uuid.uuid4()), tid, f"group:{i}")

        resp1 = test_client.get("/api/v1/finding-groups?page=1&per_page=3")
        resp2 = test_client.get("/api/v1/finding-groups?page=2&per_page=3")

        assert resp1.status_code == 200
        assert resp2.status_code == 200
        groups_p1 = {g["id"] for g in resp1.json()["groups"]}
        groups_p2 = {g["id"] for g in resp2.json()["groups"]}
        assert groups_p1 == groups_p2
        assert resp1.json()["total"] == 10
        assert resp2.json()["total"] == 10
