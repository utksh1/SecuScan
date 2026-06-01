import uuid

import pytest
import pytest_asyncio

from backend.secuscan import database as database_module
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.models import (
    NotificationChannelType,
    NotificationDeliveryStatus,
    NotificationRuleCreate,
    NotificationSeverityThreshold,
)


@pytest_asyncio.fixture
async def test_db(setup_test_environment):
    db = await init_db(settings.database_path)
    yield db
    if database_module.db is not None:
        await database_module.db.disconnect()
        database_module.db = None


@pytest.mark.asyncio
async def test_notification_tables_exist(test_db):
    tables = await test_db.fetchall(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    )
    table_names = {row["name"] for row in tables}

    assert "notification_rules" in table_names
    assert "notification_history" in table_names


@pytest.mark.asyncio
async def test_notification_rule_model_accepts_valid_payload():
    rule = NotificationRuleCreate(
        name="Production alerts",
        severity_threshold=NotificationSeverityThreshold.CRITICAL,
        channel_type=NotificationChannelType.WEBHOOK,
        target_url_or_email="https://example.com/hook",
    )

    assert rule.name == "Production alerts"
    assert rule.severity_threshold == NotificationSeverityThreshold.CRITICAL
    assert rule.channel_type == NotificationChannelType.WEBHOOK
    assert rule.is_active is True


@pytest.mark.asyncio
async def test_insert_and_read_notification_rule(test_db):
    rule_id = str(uuid.uuid4())

    await test_db.execute(
        """
        INSERT INTO notification_rules (
            id, name, severity_threshold, channel_type, target_url_or_email, is_active
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            rule_id,
            "Critical webhook",
            NotificationSeverityThreshold.CRITICAL.value,
            NotificationChannelType.WEBHOOK.value,
            "https://example.com/hook",
            1,
        ),
    )

    row = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?",
        (rule_id,),
    )

    assert row is not None
    assert row["name"] == "Critical webhook"
    assert row["severity_threshold"] == "critical"
    assert row["channel_type"] == "webhook"
    assert row["is_active"] == 1


@pytest.mark.asyncio
async def test_insert_notification_history_row(test_db):
    task_id = str(uuid.uuid4())
    finding_id = str(uuid.uuid4())
    rule_id = str(uuid.uuid4())
    history_id = str(uuid.uuid4())

    await test_db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, status, inputs_json, consent_granted
        ) VALUES (?, 'nmap', 'nmap', '127.0.0.1', 'completed', '{}', 1)
        """,
        (task_id,),
    )
    await test_db.execute(
        """
        INSERT INTO findings (
            id, task_id, plugin_id, title, category, severity, target, description, remediation
        ) VALUES (?, ?, 'nmap', 'Open port', 'network', 'critical', '127.0.0.1', 'desc', 'fix')
        """,
        (finding_id, task_id),
    )
    await test_db.execute(
        """
        INSERT INTO notification_rules (
            id, name, severity_threshold, channel_type, target_url_or_email, is_active
        ) VALUES (?, 'Critical webhook', 'critical', 'webhook', 'https://example.com/hook', 1)
        """,
        (rule_id,),
    )
    await test_db.execute(
        """
        INSERT INTO notification_history (id, rule_id, finding_id, status, error_message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            history_id,
            rule_id,
            finding_id,
            NotificationDeliveryStatus.SUCCESS.value,
            None,
        ),
    )

    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE id = ?",
        (history_id,),
    )

    assert row is not None
    assert row["rule_id"] == rule_id
    assert row["finding_id"] == finding_id
    assert row["status"] == "success"
