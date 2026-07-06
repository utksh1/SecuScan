import sqlite3
import json
import uuid

from backend.secuscan.config import settings


def _seed_completed_task(task_id: str, owner: str = "default") -> None:
    conn = sqlite3.connect(settings.database_path)
    conn.execute(
        """
        INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target, status, created_at,
                           preset, inputs_json, command_used, structured_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_id, owner, "http_inspector", "http_inspector", "https://example.com",
            "completed", "2026-05-19T10:00:00",
            "standard", json.dumps({"target": "https://example.com"}),
            "", None,
        ),
    )
    conn.commit()
    conn.close()


def _seed_findings(task_id: str, count: int, owner: str = "default") -> None:
    conn = sqlite3.connect(settings.database_path)
    severities = ["critical", "high", "medium", "low", "info"]
    rows = [
        (
            str(uuid.uuid4()), owner, task_id, "http_inspector",
            f"Finding {i}", "General", severities[i % len(severities)],
            "https://example.com", f"Description {i}",
        )
        for i in range(count)
    ]
    conn.executemany(
        """
        INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category, severity, target, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()


# Regression coverage for #1621: GET /task/{task_id}/result previously
# loaded every finding row for a task into memory with no LIMIT, which can
# OOM-crash the backend on a large scan. These tests pin down the paginated
# contract: the `findings` list respects limit/offset, while aggregate views
# (severity_counts, total_findings) always reflect the whole scan.


def test_findings_are_paginated_with_default_page_size(test_client):
    task_id = "pagination-test-001"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=250)

    response = test_client.get(f"/api/v1/task/{task_id}/result")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 100  # default per_page
    assert body["total_findings"] == 250
    assert body["page"] == 1
    assert body["per_page"] == 100
    assert body["has_more_findings"] is True


def test_findings_page_two_returns_the_next_slice(test_client):
    task_id = "pagination-test-002"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=250)

    response = test_client.get(f"/api/v1/task/{task_id}/result?page=2&per_page=100")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 100
    assert body["page"] == 2
    assert body["has_more_findings"] is True


def test_last_page_has_no_more_findings(test_client):
    task_id = "pagination-test-003"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=250)

    response = test_client.get(f"/api/v1/task/{task_id}/result?page=3&per_page=100")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 50
    assert body["has_more_findings"] is False


def test_severity_counts_reflect_the_whole_scan_not_just_the_current_page(test_client):
    task_id = "pagination-test-004"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=250)  # 50 of each severity across 5 tiers

    response = test_client.get(f"/api/v1/task/{task_id}/result?page=1&per_page=10")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 10
    assert sum(body["severity_counts"].values()) == 250
    assert body["total_findings"] == 250


def test_per_page_is_capped_at_500(test_client):
    task_id = "pagination-test-005"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=10)

    response = test_client.get(f"/api/v1/task/{task_id}/result?per_page=10000")
    assert response.status_code == 422


def test_small_scan_returns_everything_on_the_first_page(test_client):
    task_id = "pagination-test-006"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=5)

    response = test_client.get(f"/api/v1/task/{task_id}/result")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 5
    assert body["total_findings"] == 5
    assert body["has_more_findings"] is False


def test_aggregation_sample_is_capped_for_very_large_scans(test_client):
    # Simulates the issue's exact scenario: tens of thousands of findings
    # from a wide-range scan. Severity counts come from the capped
    # aggregation sample rather than every row, so they won't exactly equal
    # total_findings once the cap is exceeded -- this test documents that
    # trade-off rather than asserting exact parity.
    task_id = "pagination-test-007"
    _seed_completed_task(task_id)
    _seed_findings(task_id, count=6000)

    response = test_client.get(f"/api/v1/task/{task_id}/result")
    assert response.status_code == 200
    body = response.json()

    assert len(body["findings"]) == 100
    assert body["total_findings"] == 6000
    assert body["has_more_findings"] is True
    # Aggregation sample is capped at 5000, so severity_counts is computed
    # from at most that many rows, never all 6000.
    assert sum(body["severity_counts"].values()) <= 5000
