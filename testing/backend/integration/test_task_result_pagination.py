"""Test pagination on GET /task/{task_id}/result endpoint.

Validates that pagination works correctly while preserving exact aggregates
(severity_counts, finding_groups, asset_summary) from the complete finding set.
"""

import pytest
import asyncio
from backend.secuscan.database import get_db


async def get_task_result(client, task_id: str, limit: int = 5000, offset: int = 0):
    """Helper to fetch task result with pagination params."""
    response = client.get(
        f"/api/v1/task/{task_id}/result",
        params={"limit": limit, "offset": offset}
    )
    return response


def test_pagination_metadata_present(test_client, completed_task_with_findings):
    """Result includes pagination metadata with limit, offset, total, has_more."""
    task_id = completed_task_with_findings["id"]

    response = get_task_result(test_client, task_id, limit=10, offset=0)
    assert response.status_code == 200

    data = response.json()
    assert "pagination" in data
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["offset"] == 0
    assert data["pagination"]["total"] >= 0
    assert data["pagination"]["returned"] >= 0
    assert isinstance(data["pagination"]["has_more"], bool)


def test_pagination_limits_findings_returned(test_client, completed_task_with_findings):
    """With limit=5, only 5 findings are returned even if more exist."""
    task_id = completed_task_with_findings["id"]

    response = get_task_result(test_client, task_id, limit=5)
    assert response.status_code == 200

    data = response.json()
    assert len(data["findings"]) <= 5
    if len(data["findings"]) == 5:
        assert data["pagination"]["has_more"] is True


def test_pagination_offset_skips_findings(test_client, completed_task_with_findings):
    """With offset=5, first 5 findings are skipped."""
    task_id = completed_task_with_findings["id"]

    # Get first page
    response1 = get_task_result(test_client, task_id, limit=5, offset=0)
    assert response1.status_code == 200
    page1 = response1.json()

    # Get second page
    response2 = get_task_result(test_client, task_id, limit=5, offset=5)
    assert response2.status_code == 200
    page2 = response2.json()

    # Finding sets should be different (if enough findings exist)
    if page1["pagination"]["total"] > 5:
        page1_ids = {f.get("id") for f in page1["findings"]}
        page2_ids = {f.get("id") for f in page2["findings"]}
        assert page1_ids != page2_ids or not page1_ids  # Either different or empty


def test_aggregates_same_with_pagination(test_client, completed_task_with_findings):
    """severity_counts, finding_groups, asset_summary are identical regardless of pagination."""
    task_id = completed_task_with_findings["id"]

    # Get result without pagination
    response_full = get_task_result(test_client, task_id, limit=50000, offset=0)
    assert response_full.status_code == 200
    full = response_full.json()

    # Get result with pagination (limit=5)
    response_page1 = get_task_result(test_client, task_id, limit=5, offset=0)
    assert response_page1.status_code == 200
    page1 = response_page1.json()

    # Aggregates should match exactly
    assert full["severity_counts"] == page1["severity_counts"]
    assert full["finding_groups"] == page1["finding_groups"]
    assert full["asset_summary"] == page1["asset_summary"]

    # But findings count should differ if there are more than 5
    if full["pagination"]["total"] > 5:
        assert len(full["findings"]) != len(page1["findings"])


def test_pagination_default_limit(test_client, completed_task_with_findings):
    """Default limit is 5000 when not specified."""
    task_id = completed_task_with_findings["id"]

    response = get_task_result(test_client, task_id)
    assert response.status_code == 200

    data = response.json()
    assert data["pagination"]["limit"] == 5000


def test_pagination_boundary_checks(test_client, completed_task_with_findings):
    """Offset beyond total findings returns empty list."""
    task_id = completed_task_with_findings["id"]

    # Get total count
    response1 = get_task_result(test_client, task_id, limit=50000)
    total = response1.json()["pagination"]["total"]

    # Request beyond total
    response2 = get_task_result(test_client, task_id, limit=5, offset=total + 100)
    assert response2.status_code == 200

    data = response2.json()
    assert len(data["findings"]) == 0
    assert data["pagination"]["has_more"] is False
    assert data["pagination"]["total"] == total  # Aggregate still accurate
