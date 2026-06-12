"""
Tests for finding redaction before DB insert and structured_json regression.

Covers:
  - description, remediation, proof are redacted in the `findings` row
  - tasks.structured_json is redacted for both the plugin and modular-scanner paths
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.secuscan.redaction import REDACTED


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_finding(**overrides):
    base = {
        "title": "Test Finding",
        "category": "Security",
        "severity": "high",
        "description": "Secret token=abc123deadbeef0011223344556677889900aabbcc",
        "remediation": "Remove password=hunter2 from config",
        "proof": "Bearer ghp_supersecrettoken1234567890abcdef1234",
    }
    base.update(overrides)
    return base


def _make_db_mock():
    db = AsyncMock()
    db.execute = AsyncMock()
    db.fetchone = AsyncMock(return_value=None)
    db.fetchall = AsyncMock(return_value=[])
    db.log_audit = AsyncMock()
    return db


# ── _persist_finding ───────────────────────────────────────────────────────────

class TestPersistFindingRedaction:
    """Verify that description, remediation, and proof are redacted before INSERT."""

    @pytest.mark.asyncio
    async def test_description_redacted_in_insert(self):
        from backend.secuscan.executor import TaskExecutor

        executor = TaskExecutor()
        db = _make_db_mock()
        finding = _make_finding(
            description="API key found: api_key=SUPERSECRET12345678",
            remediation="No secrets here",
            proof=None,
        )

        await executor._persist_finding(
            db,
            owner_id="owner1",
            task_id="task1",
            plugin_id="plugin1",
            target="example.com",
            finding=finding,
        )

        assert db.execute.called
        call_args = db.execute.call_args[0]
        values = call_args[1]
        # description is at index 8 in the INSERT values tuple
        description_idx = 8
        assert REDACTED in values[description_idx], (
            f"description not redacted; got: {values[description_idx]!r}"
        )
        assert "SUPERSECRET12345678" not in values[description_idx]

    @pytest.mark.asyncio
    async def test_remediation_redacted_in_insert(self):
        from backend.secuscan.executor import TaskExecutor

        executor = TaskExecutor()
        db = _make_db_mock()
        finding = _make_finding(
            description="No secrets",
            remediation="Reset the password=hunter2 immediately",
            proof=None,
        )

        await executor._persist_finding(
            db,
            owner_id="owner1",
            task_id="task1",
            plugin_id="plugin1",
            target="example.com",
            finding=finding,
        )

        values = db.execute.call_args[0][1]
        remediation_idx = 9
        assert REDACTED in values[remediation_idx], (
            f"remediation not redacted; got: {values[remediation_idx]!r}"
        )
        assert "hunter2" not in values[remediation_idx]

    @pytest.mark.asyncio
    async def test_proof_redacted_in_insert(self):
        from backend.secuscan.executor import TaskExecutor

        executor = TaskExecutor()
        db = _make_db_mock()
        finding = _make_finding(
            description="No secrets",
            remediation="No secrets",
            proof="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.sig",
        )

        await executor._persist_finding(
            db,
            owner_id="owner1",
            task_id="task1",
            plugin_id="plugin1",
            target="example.com",
            finding=finding,
        )

        values = db.execute.call_args[0][1]
        proof_idx = 10
        assert REDACTED in values[proof_idx], (
            f"proof not redacted; got: {values[proof_idx]!r}"
        )

    @pytest.mark.asyncio
    async def test_clean_finding_passes_through_unchanged(self):
        from backend.secuscan.executor import TaskExecutor

        executor = TaskExecutor()
        db = _make_db_mock()
        finding = _make_finding(
            description="Open port 443 detected on example.com",
            remediation="Close unnecessary ports using a firewall.",
            proof="nmap output line 42",
        )

        await executor._persist_finding(
            db,
            owner_id="owner1",
            task_id="task1",
            plugin_id="plugin1",
            target="example.com",
            finding=finding,
        )

        values = db.execute.call_args[0][1]
        assert values[8] == finding["description"]
        assert values[9] == finding["remediation"]
        assert values[10] == finding["proof"]


# ── structured_json redaction ──────────────────────────────────────────────────

SECRET_FINDING = {
    "title": "Credential Leak",
    "category": "Secrets",
    "severity": "critical",
    "description": "Found api_key=0102030405060708090a0b0c0d0e0f10 in response body",
    "remediation": "Rotate the key immediately",
    "proof": None,
}


def _build_mock_executor_for_upsert():
    from backend.secuscan.executor import TaskExecutor

    executor = TaskExecutor()

    async def _fake_build_result(db, *, task_id, owner_id, plugin_id, target, result):
        structured = dict(result)
        structured.setdefault("findings", result.get("findings", []))
        return structured, [], []

    async def _fake_persist(db, *, owner_id, task_id, plugin_id, target, finding):
        return {**finding, "id": f"finding:{task_id}:aabbccdd", "plugin_id": plugin_id}

    executor._build_result_contract = _fake_build_result
    executor._persist_finding = _fake_persist
    executor._persist_result_resources = AsyncMock()
    executor._build_severity_counts = MagicMock(return_value={"critical": 1})
    return executor


class TestStructuredJsonRedaction:
    """Verify tasks.structured_json is redacted before the UPDATE write."""

    @pytest.mark.asyncio
    async def test_upsert_findings_and_report_redacts_structured_json(self):
        executor = _build_mock_executor_for_upsert()
        db = _make_db_mock()

        plugin = MagicMock()
        plugin.name = "test-plugin"
        plugin.output = {}

        with patch("backend.secuscan.executor.build_finding_groups", return_value=[]), \
             patch("backend.secuscan.executor.build_asset_summary", return_value={}), \
             patch("backend.secuscan.executor.build_scan_diff", return_value={}):
            await executor._upsert_findings_and_report(
                db,
                task_id="task-redact-1",
                owner_id="owner1",
                plugin=plugin,
                plugin_id="plugin1",
                target="example.com",
                status="completed",
                output="",
            )

        update_call = next(
            (c for c in db.execute.call_args_list if "structured_json" in c[0][0]),
            None,
        )
        assert update_call is not None, "No structured_json UPDATE call found"
        stored_json = update_call[0][1][0]
        stored = json.loads(stored_json)

        for f in stored.get("findings", []):
            desc = f.get("description", "")
            assert "0102030405060708090a0b0c0d0e0f10" not in desc, (
                f"Secret leaked into structured_json finding description: {desc!r}"
            )

    @pytest.mark.asyncio
    async def test_upsert_findings_and_report_from_scanner_redacts_structured_json(self):
        executor = _build_mock_executor_for_upsert()
        db = _make_db_mock()

        scanner = MagicMock()
        scanner.name = "modular-scanner"

        raw_result = {
            "status": "completed",
            "findings": [SECRET_FINDING],
        }

        with patch("backend.secuscan.executor.build_finding_groups", return_value=[]), \
             patch("backend.secuscan.executor.build_asset_summary", return_value={}), \
             patch("backend.secuscan.executor.build_scan_diff", return_value={}):
            await executor._upsert_findings_and_report_from_scanner(
                db,
                task_id="task-redact-2",
                owner_id="owner1",
                scanner=scanner,
                plugin_id="plugin2",
                target="example.com",
                status="completed",
                result=raw_result,
            )

        update_call = next(
            (c for c in db.execute.call_args_list if "structured_json" in c[0][0]),
            None,
        )
        assert update_call is not None, "No structured_json UPDATE call found"
        stored_json = update_call[0][1][0]
        stored = json.loads(stored_json)

        for f in stored.get("findings", []):
            desc = f.get("description", "")
            assert "0102030405060708090a0b0c0d0e0f10" not in desc, (
                f"Secret leaked into structured_json (modular scanner path): {desc!r}"
            )