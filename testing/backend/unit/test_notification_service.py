import json
import socket
import uuid
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from backend.secuscan import database as database_module
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.models import (
    NotificationChannelType,
    NotificationDeliveryStatus,
    NotificationSeverityThreshold,
)
from backend.secuscan.notification_service import (
    build_alert_payload,
    deliver_via_rule,
    process_finding_notifications,
    severity_meets_threshold,
    was_already_delivered,
)
from backend.secuscan.redaction import REDACTED


@pytest_asyncio.fixture
async def test_db(setup_test_environment):
    db = await init_db(settings.database_path)
    yield db
    if database_module.db is not None:
        await database_module.db.disconnect()
        database_module.db = None


async def _seed_finding(
    db,
    *,
    severity: str = "critical",
    description: str = "Open port on target",
) -> tuple[str, str]:
    task_id = str(uuid.uuid4())
    finding_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, status, inputs_json, consent_granted
        ) VALUES (?, 'nmap', 'nmap', '127.0.0.1', 'completed', '{}', 1)
        """,
        (task_id,),
    )
    await db.execute(
        """
        INSERT INTO findings (
            id, task_id, plugin_id, title, category, severity, target, description, remediation
        ) VALUES (?, ?, 'nmap', 'Open port', 'network', ?, '127.0.0.1', ?, 'fix')
        """,
        (finding_id, task_id, severity, description),
    )
    return task_id, finding_id


async def _seed_rule(
    db,
    *,
    severity_threshold: str = NotificationSeverityThreshold.HIGH.value,
    channel_type: str = NotificationChannelType.WEBHOOK.value,
    target: str = "https://example.com/hook",
    is_active: int = 1,
) -> str:
    rule_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO notification_rules (
            id, name, severity_threshold, channel_type, target_url_or_email, is_active
        ) VALUES (?, 'Test rule', ?, ?, ?, ?)
        """,
        (rule_id, severity_threshold, channel_type, target, is_active),
    )
    return rule_id


def test_severity_meets_threshold():
    assert severity_meets_threshold("critical", "high") is True
    assert severity_meets_threshold("high", "high") is True
    assert severity_meets_threshold("medium", "high") is False
    assert severity_meets_threshold("info", "critical") is False


@pytest.mark.asyncio
async def test_build_alert_payload_redacts_secrets():
    finding = {
        "id": "f1",
        "task_id": "t1",
        "plugin_id": "nmap",
        "title": "Secret leak",
        "category": "network",
        "severity": "critical",
        "target": "127.0.0.1",
        "description": "Authorization: Bearer supersecrettoken12345678",
        "remediation": "",
        "metadata_json": json.dumps({"api_key": "abc123secret"}),
    }
    rule = {
        "id": "r1",
        "name": "Alerts",
        "severity_threshold": "high",
        "channel_type": "webhook",
    }

    payload = build_alert_payload(finding, rule)

    assert REDACTED in payload["finding"]["description"]
    assert "supersecrettoken12345678" not in payload["finding"]["description"]
    assert payload["finding"]["metadata"]["api_key"] == REDACTED


@pytest.mark.asyncio
async def test_deliver_via_rule_sends_webhook_and_records_history(test_db):
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db)

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(True, None)),
    ):
        result = await deliver_via_rule(test_db, rule, finding)

    assert result.status == NotificationDeliveryStatus.SUCCESS
    assert result.skipped is False
    assert await was_already_delivered(test_db, rule_id, finding_id) is True


@pytest.mark.asyncio
async def test_deliver_via_rule_dedupes_second_attempt(test_db):
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db)

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    mock_send = AsyncMock(return_value=(True, None))
    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=mock_send,
    ):
        first = await deliver_via_rule(test_db, rule, finding)
        second = await deliver_via_rule(test_db, rule, finding)

    assert first.status == NotificationDeliveryStatus.SUCCESS
    assert second.skipped is True
    assert mock_send.await_count == 1


@pytest.mark.asyncio
async def test_deliver_skips_below_threshold(test_db):
    _, finding_id = await _seed_finding(test_db, severity="low")
    rule_id = await _seed_rule(test_db, severity_threshold="high")

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    result = await deliver_via_rule(test_db, rule, finding)

    assert result.skipped is True
    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
        (rule_id, finding_id),
    )
    assert row is None


@pytest.mark.asyncio
async def test_deliver_records_failure_on_webhook_error(test_db):
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db)

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(False, "connection refused")),
    ):
        result = await deliver_via_rule(test_db, rule, finding)

    assert result.status == NotificationDeliveryStatus.FAILED
    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
        (rule_id, finding_id),
    )
    assert row is not None
    assert row["status"] == NotificationDeliveryStatus.FAILED.value
    assert row["error_message"] == "connection refused"


@pytest.mark.asyncio
async def test_email_placeholder_records_success(test_db):
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(
        test_db,
        channel_type=NotificationChannelType.EMAIL.value,
        target="alerts@example.com",
    )

    results = await process_finding_notifications(test_db, finding_id)

    assert len(results) == 1
    assert results[0].status == NotificationDeliveryStatus.SUCCESS
    assert results[0].skipped is False


def _mock_async_client(mock_post):
    """Helper to mock httpx.AsyncClient as an async context manager."""
    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client
    return mock_cm


@pytest.mark.asyncio
async def test_send_webhook_success():
    """Normal webhook delivery succeeds."""
    from backend.secuscan.notification_service import send_webhook

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)), patch("backend.secuscan.notification_service.socket.getaddrinfo", return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):
        ok, err = await send_webhook("https://hooks.example.com/alert", {"event": "test"})
               return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):

    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_send_webhook_http_error():
    """Webhook returning >=400 is reported as failure."""
    from backend.secuscan.notification_service import send_webhook

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_post = AsyncMock(return_value=mock_response)
    with patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)), patch("backend.secuscan.notification_service.socket.getaddrinfo", return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):
        ok, err = await send_webhook("https://hooks.example.com/alert", {"event": "test"})
         patch("backend.secuscan.notification_service.socket.getaddrinfo",
               return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):

    assert ok is False
    assert "500" in err


@pytest.mark.asyncio
async def test_send_webhook_http_exception():
    """Transport-level errors are caught and returned as failure."""
    from backend.secuscan.notification_service import send_webhook

    with patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)), patch("backend.secuscan.notification_service.socket.getaddrinfo", return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):
        ok, err = await send_webhook("https://hooks.example.com/alert", {"event": "test"})
    with patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)), \
         patch("backend.secuscan.notification_service.socket.getaddrinfo",
               return_value=[(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]):

    assert ok is False
    assert "Connection refused" in err


@pytest.mark.asyncio
async def test_send_webhook_redirect_to_blocked_ip():
    """Redirect to a private IP (SSRF) is rejected after delivery."""
    from backend.secuscan.notification_service import send_webhook

    mock_response = AsyncMock()
    mock_response.status_code = 302
    mock_response.headers = {"location": "http://10.0.0.1/evil"}
    mock_post = AsyncMock(return_value=mock_response)

    with (
        patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)),
        patch("backend.secuscan.notification_service.socket.getaddrinfo",
              return_value=[(socket.AF_INET, None, None, None, ("10.0.0.1", 80))]),
    ):
        ok, err = await send_webhook("https://hooks.example.com/alert", {"event": "test"})

    assert ok is False
    assert "blocked" in err.lower()
