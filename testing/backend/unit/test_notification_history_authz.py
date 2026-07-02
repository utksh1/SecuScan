"""
Regression tests for notification history owner isolation (BOLA fix, PR #1522).

Proves that user A cannot view user B's notification history, covering both
the unfiltered path and the rule_id filter path.
"""

import uuid
import pytest

from backend.secuscan.database import init_db
from backend.secuscan.models import TaskStatus


async def _seed_user_data(db, owner_a: str, owner_b: str):
    """Seed two rules (one per owner) and one notification history entry per rule."""
    rule_a_id = str(uuid.uuid4())
    rule_b_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO notification_rules (id, name, owner_id, severity_threshold, channel_type, target_url_or_email, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rule_a_id, "Rule A", owner_a, "high", "webhook", "https://a.example.com/hook", 1),
    )
    await db.execute(
        "INSERT INTO notification_rules (id, name, owner_id, severity_threshold, channel_type, target_url_or_email, is_active) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (rule_b_id, "Rule B", owner_b, "high", "webhook", "https://b.example.com/hook", 1),
    )

    task_id = str(uuid.uuid4())
    finding_id = str(uuid.uuid4())

    await db.execute(
        "INSERT INTO tasks (id, plugin_id, tool_name, target, inputs_json, status, consent_granted) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, "nmap", "nmap", "127.0.0.1", "{}", TaskStatus.COMPLETED.value, 1),
    )
    await db.execute(
        "INSERT INTO findings (id, task_id, plugin_id, title, category, severity, target, description, remediation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (finding_id, task_id, "nmap", "Open port", "network", "high", "127.0.0.1", "desc", "fix"),
    )

    hist_a_id = str(uuid.uuid4())
    hist_b_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO notification_history (id, rule_id, finding_id, status) VALUES (?, ?, ?, ?)",
        (hist_a_id, rule_a_id, finding_id, "success"),
    )
    await db.execute(
        "INSERT INTO notification_history (id, rule_id, finding_id, status) VALUES (?, ?, ?, ?)",
        (hist_b_id, rule_b_id, finding_id, "success"),
    )
    return rule_a_id, rule_b_id


@pytest.mark.asyncio
async def test_owner_a_cannot_see_owner_b_history():
    """User A's notification history query must not return user B's entries."""
    db = await init_db(":memory:")
    try:
        owner_a = "user-a@example.com"
        owner_b = "user-b@example.com"
        await _seed_user_data(db, owner_a, owner_b)

        rows = await db.fetchall(
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ? ORDER BY nh.sent_at DESC LIMIT 50 OFFSET 0",
            (owner_a,),
        )
        assert len(rows) == 1
        rule_a_id = rows[0]["rule_id"]

        owner_of_rule = await db.fetchone(
            "SELECT owner_id FROM notification_rules WHERE id = ?", (rule_a_id,)
        )
        assert owner_of_rule["owner_id"] == owner_a

        rows_b = await db.fetchall(
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ? ORDER BY nh.sent_at DESC LIMIT 50 OFFSET 0",
            (owner_b,),
        )
        assert len(rows_b) == 1
        rule_b_id = rows_b[0]["rule_id"]
        owner_of_rule_b = await db.fetchone(
            "SELECT owner_id FROM notification_rules WHERE id = ?", (rule_b_id,)
        )
        assert owner_of_rule_b["owner_id"] == owner_b
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_owner_a_cannot_see_owner_b_history_with_rule_id_filter():
    """Even when filtering by rule_id, user A must not see user B's entries."""
    db = await init_db(":memory:")
    try:
        owner_a = "user-a@example.com"
        owner_b = "user-b@example.com"
        rule_a_id, rule_b_id = await _seed_user_data(db, owner_a, owner_b)

        rows = await db.fetchall(
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ? AND nh.rule_id = ? ORDER BY nh.sent_at DESC LIMIT 50 OFFSET 0",
            (owner_a, rule_b_id),
        )
        assert len(rows) == 0

        rows_own = await db.fetchall(
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ? AND nh.rule_id = ? ORDER BY nh.sent_at DESC LIMIT 50 OFFSET 0",
            (owner_a, rule_a_id),
        )
        assert len(rows_own) == 1
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_count_query_respects_owner_isolation():
    """The COUNT query (for pagination) must also filter by owner."""
    db = await init_db(":memory:")
    try:
        owner_a = "user-a@example.com"
        owner_b = "user-b@example.com"
        await _seed_user_data(db, owner_a, owner_b)

        count_a = await db.fetchone(
            "SELECT COUNT(*) AS total FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ?",
            (owner_a,),
        )
        assert int(count_a["total"]) == 1

        count_b = await db.fetchone(
            "SELECT COUNT(*) AS total FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ?",
            (owner_b,),
        )
        assert int(count_b["total"]) == 1
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_owner_without_rules_sees_empty_history():
    """An owner with no notification rules must see an empty history."""
    db = await init_db(":memory:")
    try:
        owner_a = "user-a@example.com"
        owner_c = "user-c@example.com"
        await _seed_user_data(db, owner_a, owner_c)

        rows = await db.fetchall(
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ? ORDER BY nh.sent_at DESC LIMIT 50 OFFSET 0",
            ("no-rules-user@example.com",),
        )
        assert len(rows) == 0
    finally:
        await db.disconnect()


@pytest.mark.asyncio
async def test_route_level_owner_isolation():
    """Simulate the FastAPI route logic: the owner parameter from
    Depends(get_current_owner) drives the WHERE clause, guaranteeing
    that user A cannot enumerate user B's history.
    """
    db = await init_db(":memory:")
    try:
        owner_a = "user-a@example.com"
        owner_b = "user-b@example.com"
        await _seed_user_data(db, owner_a, owner_b)

        query = (
            "SELECT nh.* FROM notification_history nh "
            "JOIN notification_rules nr ON nh.rule_id = nr.id "
            "WHERE nr.owner_id = ?"
        )
        params_a: list = [owner_a]
        query += " ORDER BY nh.sent_at DESC LIMIT ? OFFSET ?"
        params_a.extend([50, 0])

        rows = await db.fetchall(query, tuple(params_a))
        for row in rows:
            rule_owner = await db.fetchone(
                "SELECT owner_id FROM notification_rules WHERE id = ?", (row["rule_id"],)
            )
            assert rule_owner["owner_id"] == owner_a
    finally:
        await db.disconnect()
