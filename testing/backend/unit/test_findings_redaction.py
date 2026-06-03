"""
Unit and integration tests for findings redaction before DB persistence.

Verifies that secrets are stripped from finding fields (description,
remediation, proof) and from tasks.structured_json before any DB write.

Run with:
    ./testing/test_python.sh
or directly:
    pytest testing/backend/unit/test_findings_redaction.py -v
"""

import json
import uuid
from unittest.mock import patch

import pytest

from backend.secuscan.config import settings
from backend.secuscan.database import get_db, init_db
from backend.secuscan.plugins import get_plugin_manager, init_plugins
from backend.secuscan.redaction import redact_dict, REDACTED


# ── Fake AWS key used across tests ────────────────────────────────────────────

FAKE_AWS_KEY = "AKIAIOSFODNN7EXAMPLE"


# ── Unit tests: redact_dict behaviour ─────────────────────────────────────────

def test_redact_dict_redacts_aws_key_in_description():
    """Secret in description and remediation is replaced with [REDACTED]."""
    finding = {
        "title": "Exposed credential",
        "category": "Secrets",
        "severity": "critical",
        "description": f"Found credential {FAKE_AWS_KEY} in config.",
        "remediation": f"Rotate the key {FAKE_AWS_KEY} immediately.",
    }
    result = redact_dict(finding)
    assert REDACTED in result["description"]
    assert FAKE_AWS_KEY not in result["description"]
    assert REDACTED in result["remediation"]
    assert FAKE_AWS_KEY not in result["remediation"]


def test_redact_dict_leaves_clean_finding_unchanged():
    """Clean findings with no secrets pass through unmodified."""
    finding = {
        "title": "Open Port",
        "category": "Network",
        "severity": "low",
        "description": "Port 80 is open and running http.",
        "remediation": "Close unnecessary ports.",
    }
    result = redact_dict(finding)
    assert result["description"] == finding["description"]
    assert result["remediation"] == finding["remediation"]
    assert result["title"] == finding["title"]


def test_redact_dict_handles_nested_metadata():
    """Nested metadata dict is walked recursively; non-strings are untouched."""
    finding = {
        "title": "Secret in metadata",
        "severity": "high",
        "description": "See metadata.",
        "metadata": {
            "raw_value": f"key={FAKE_AWS_KEY}",
            "port": 443,
            "nested": {"token": f"Bearer {FAKE_AWS_KEY}"},
        },
    }
    result = redact_dict(finding)
    assert FAKE_AWS_KEY not in result["metadata"]["raw_value"]
    assert result["metadata"]["port"] == 443  # int untouched
    assert FAKE_AWS_KEY not in result["metadata"]["nested"]["token"]


def test_redact_dict_handles_none_proof():
    """None proof field does not raise and is returned as-is."""
    finding = {
        "title": "Finding",
        "severity": "info",
        "description": "No proof available.",
        "proof": None,
    }
    result = redact_dict(finding)
    assert result["proof"] is None


def test_redact_dict_handles_missing_keys_gracefully():
    """Minimal finding dict with no description/remediation/proof works fine."""
    finding = {"title": "Bare finding", "severity": "low"}
    result = redact_dict(finding)
    assert result["title"] == "Bare finding"
    assert result["severity"] == "low"


# ── Integration test: DB persistence paths ────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_findings_redacts_description_before_insert(setup_test_environment):
    """
    After _upsert_findings_and_report is called:
    1. The findings table row must not contain the raw secret.
    2. tasks.structured_json must not contain the raw secret.
    """
    from backend.secuscan.executor import TaskExecutor

    # Initialise a fresh temp DB (setup_test_environment sets settings.database_path to a tmp dir)
    await init_db(settings.database_path)
    db = await get_db()

    # Ensure plugins are loaded
    try:
        pm = get_plugin_manager()
    except RuntimeError:
        await init_plugins(settings.plugins_dir)
        pm = get_plugin_manager()

    plugin_id = next(iter(pm.plugins))
    plugin = pm.get_plugin(plugin_id)

    task_id = str(uuid.uuid4())

    # Insert a minimal task row so foreign-key constraints are satisfied
    await db.execute(
        """
        INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, status, scan_phase, safe_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (task_id, plugin_id, plugin.name, "example.com",
         json.dumps({"target": "example.com"}), "running", "running_command", 0),
    )

    tainted_finding = {
        "title": "Exposed AWS key",
        "category": "Secrets",
        "severity": "critical",
        "description": f"AWS key found: {FAKE_AWS_KEY}",
        "remediation": f"Rotate {FAKE_AWS_KEY} immediately.",
        "proof": f"curl response contained {FAKE_AWS_KEY}",
        "metadata": {},
    }

    executor = TaskExecutor()
    with patch.object(executor, "_parse_results", return_value={"findings": [tainted_finding]}):
        await executor._upsert_findings_and_report(
            db=db,
            task_id=task_id,
            plugin=plugin,
            plugin_id=plugin_id,
            target="example.com",
            status="completed",
            output="",
        )

    # Assert: findings table row is clean
    row = await db.fetchone(
        "SELECT description, remediation, proof FROM findings WHERE task_id = ?",
        (task_id,),
    )
    assert row is not None, "No finding row was inserted"
    assert FAKE_AWS_KEY not in (row["description"] or ""), \
        f"Secret still in findings.description: {row['description']!r}"
    assert FAKE_AWS_KEY not in (row["remediation"] or ""), \
        f"Secret still in findings.remediation: {row['remediation']!r}"
    assert FAKE_AWS_KEY not in (row["proof"] or ""), \
        f"Secret still in findings.proof: {row['proof']!r}"

    # Assert: structured_json is also clean
    task_row = await db.fetchone(
        "SELECT structured_json FROM tasks WHERE id = ?",
        (task_id,),
    )
    assert task_row is not None
    structured = json.loads(task_row["structured_json"])
    findings_in_structured = structured.get("findings", [])
    assert findings_in_structured, "structured_json contained no findings"
    first = findings_in_structured[0]
    assert FAKE_AWS_KEY not in (first.get("description") or ""), \
        f"Secret still in structured_json finding description: {first.get('description')!r}"
    assert FAKE_AWS_KEY not in (first.get("remediation") or ""), \
        f"Secret still in structured_json finding remediation: {first.get('remediation')!r}"
    assert FAKE_AWS_KEY not in (first.get("proof") or ""), \
        f"Secret still in structured_json finding proof: {first.get('proof')!r}"