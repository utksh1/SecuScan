"""
Unit tests for _gather_scan_summary in backend/secuscan/notification_service.py.

The function collects task status, severity counts, and a report link for scan
completion webhooks. It is exercised indirectly through process_scan_completion_webhook
but not directly unit tested.
"""

from __future__ import annotations

import tempfile
import uuid

import pytest
import pytest_asyncio

from backend.secuscan import database as database_module
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.notification_service import _gather_scan_summary


@pytest.fixture
def setup_test_environment(monkeypatch):
    """Override settings for tests to ensure isolated execution."""
    temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    temp_path = temp_dir.name

    monkeypatch.setattr(settings, "data_dir", temp_path)
    monkeypatch.setattr(settings, "raw_output_dir", f"{temp_path}/raw")
    monkeypatch.setattr(settings, "reports_dir", f"{temp_path}/reports")
    monkeypatch.setattr(settings, "database_path", f"{temp_path}/test_secuscan.db")
    monkeypatch.setattr(settings, "vault_key", "test-vault-key-for-unit-tests-only")
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-key")
    monkeypatch.setattr(settings, "enforce_network_policy", False)
    monkeypatch.setattr(settings, "scan_rate_limit", 0)

    settings.ensure_directories()

    yield temp_path

    temp_dir.cleanup()


@pytest_asyncio.fixture
async def test_db(setup_test_environment):
    db = await init_db(settings.database_path)
    yield db
    if database_module.db is not None:
        await database_module.db.disconnect()
        database_module.db = None


async def _seed_task_with_findings(
    db,
    *,
    status: str = "completed",
    findings: list[str] | None = None,
    tool_name: str = "nmap",
    plugin_id: str = "nmap",
    owner_id: str = "default",
    error_message: str | None = None,
) -> tuple[str, list[str]]:
    """Seed a task and optionally seed findings with given severities."""
    task_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, status, inputs_json, consent_granted, owner_id
        ) VALUES (?, ?, ?, ?, ?, '{}', 1, ?)
        """,
        (task_id, plugin_id, tool_name, "https://example.com", status, owner_id),
    )
    if error_message:
        await db.execute(
            "UPDATE tasks SET error_message = ? WHERE id = ?",
            (error_message, task_id),
        )

    finding_ids = []
    severities = findings or []
    for severity in severities:
        finding_id = str(uuid.uuid4())
        finding_ids.append(finding_id)
        await db.execute(
            """
            INSERT INTO findings (
                id, task_id, plugin_id, title, category, severity, target, description, remediation
            ) VALUES (?, ?, ?, 'Open port', 'network', ?, 'https://example.com', 'desc', 'fix')
            """,
            (finding_id, task_id, plugin_id, severity),
        )
    return task_id, finding_ids


@pytest.mark.asyncio
async def test_returns_none_for_nonexistent_task(test_db):
    """_gather_scan_summary returns None when the task does not exist."""
    result = await _gather_scan_summary(test_db, str(uuid.uuid4()))
    assert result is None


@pytest.mark.asyncio
async def test_returns_correct_summary_dict(test_db):
    """_gather_scan_summary returns a dict with expected keys."""
    task_id, _ = await _seed_task_with_findings(test_db)
    result = await _gather_scan_summary(test_db, task_id)
    assert result is not None
    assert "task_id" in result
    assert "tool_name" in result
    assert "target" in result
    assert "status" in result
    assert "total_findings" in result
    assert "severity_counts" in result
    assert "error_message" in result
    assert "report_link" in result


@pytest.mark.asyncio
async def test_severity_counts_are_correct(test_db):
    """Severity counts are correctly aggregated."""
    task_id, _ = await _seed_task_with_findings(
        test_db,
        findings=["critical", "critical", "high", "low"],
    )
    result = await _gather_scan_summary(test_db, task_id)
    assert result["total_findings"] == 4
    assert result["severity_counts"]["critical"] == 2
    assert result["severity_counts"]["high"] == 1
    assert result["severity_counts"]["low"] == 1


@pytest.mark.asyncio
async def test_zero_findings_gives_zero_counts(test_db):
    """A completed task with no findings has total_findings=0 and empty counts."""
    task_id, _ = await _seed_task_with_findings(test_db)
    result = await _gather_scan_summary(test_db, task_id)
    assert result["total_findings"] == 0
    assert result["severity_counts"] == {}


@pytest.mark.asyncio
async def test_error_message_included_in_summary(test_db):
    """error_message from the task is included in the summary."""
    task_id, _ = await _seed_task_with_findings(
        test_db,
        status="failed",
        error_message="Connection refused",
    )
    result = await _gather_scan_summary(test_db, task_id)
    assert result["error_message"] == "Connection refused"


@pytest.mark.asyncio
async def test_report_link_contains_task_id(test_db):
    """The report link contains the task_id."""
    task_id, _ = await _seed_task_with_findings(test_db)
    result = await _gather_scan_summary(test_db, task_id)
    assert task_id in result["report_link"]


@pytest.mark.asyncio
async def test_status_lowercased(test_db):
    """The status in the summary is lowercased."""
    task_id, _ = await _seed_task_with_findings(test_db, status="COMPLETED")
    result = await _gather_scan_summary(test_db, task_id)
    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_tool_name_uses_database_value(test_db):
    """tool_name in the summary matches the database value."""
    task_id, _ = await _seed_task_with_findings(test_db, tool_name="sqlmap")
    result = await _gather_scan_summary(test_db, task_id)
    assert result["tool_name"] == "sqlmap"
