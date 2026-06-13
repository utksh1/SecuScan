import sqlite3
import json
import pytest
from backend.secuscan.config import settings

ALICE = {"X-User-Id": "alice"}
ALICE_OWNER = "user:alice"

def _seed_task(owner_id: str, task_id: str) -> None:
    """Insert a task row directly with an explicit owner_id."""
    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            """
            INSERT INTO tasks (id, owner_id, plugin_id, tool_name, target,
                               status, inputs_json, structured_json, consent_granted)
            VALUES (?, ?, 'nmap', 'nmap', '127.0.0.1', 'completed', '{}', '{"findings": []}', 1)
            """,
            (task_id, owner_id),
        )
        conn.commit()
    finally:
        conn.close()

def _seed_finding(owner_id: str, finding_id: str, task_id: str, metadata: dict | None = None) -> None:
    conn = sqlite3.connect(settings.database_path)
    metadata_json = json.dumps(metadata) if metadata is not None else None
    try:
        conn.execute(
            """
            INSERT INTO findings (id, owner_id, task_id, plugin_id, title, category,
                                  severity, target, description, remediation, metadata_json)
            VALUES (?, ?, ?, 'nmap', 'Open port', 'network', 'low', '127.0.0.1', 'desc', 'fix', ?)
            """,
            (finding_id, owner_id, task_id, metadata_json),
        )
        conn.commit()
    finally:
        conn.close()

def test_routes_expose_remediation_safety_fields(test_client):
    """Test that safe_to_apply, compatible_range, and alternatives fields are exposed in API responses when present in metadata, and default to None otherwise."""
    _seed_task(ALICE_OWNER, "task-1")

    # 1. Seed finding with validated remediation metadata
    metadata_validated = {
        "safe_to_apply": False,
        "compatible_range": "<2.0",
        "alternatives": ["Upgrade package-y"],
        "other_key": "some_value"
    }
    _seed_finding(ALICE_OWNER, "finding-validated", "task-1", metadata=metadata_validated)

    # 2. Seed finding without validated remediation metadata
    metadata_unvalidated = {
        "other_key": "some_value"
    }
    _seed_finding(ALICE_OWNER, "finding-unvalidated", "task-1", metadata=metadata_unvalidated)

    # 3. Test `/findings` list endpoint
    response_list = test_client.get("/api/v1/findings", headers=ALICE)
    assert response_list.status_code == 200
    findings_list = response_list.json()["findings"]

    finding_val = next(f for f in findings_list if f["id"] == "finding-validated")
    assert finding_val["safe_to_apply"] is False
    assert finding_val["compatible_range"] == "<2.0"
    assert finding_val["alternatives"] == ["Upgrade package-y"]

    finding_unval = next(f for f in findings_list if f["id"] == "finding-unvalidated")
    assert finding_unval["safe_to_apply"] is None
    assert finding_unval["compatible_range"] is None
    assert finding_unval["alternatives"] is None

    # 4. Test `/finding/{finding_id}` detail endpoint - Validated Case
    response_detail_val = test_client.get("/api/v1/finding/finding-validated", headers=ALICE)
    assert response_detail_val.status_code == 200
    detail_val = response_detail_val.json()
    assert detail_val["safe_to_apply"] is False
    assert detail_val["compatible_range"] == "<2.0"
    assert detail_val["alternatives"] == ["Upgrade package-y"]

    # 5. Test `/finding/{finding_id}` detail endpoint - Unvalidated Case
    response_detail_unval = test_client.get("/api/v1/finding/finding-unvalidated", headers=ALICE)
    assert response_detail_unval.status_code == 200
    detail_unval = response_detail_unval.json()
    assert detail_unval["safe_to_apply"] is None
    assert detail_unval["compatible_range"] is None
    assert detail_unval["alternatives"] is None
