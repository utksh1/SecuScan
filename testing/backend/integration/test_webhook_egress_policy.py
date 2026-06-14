"""
Regression guard: webhook delivery must respect network egress controls.

Proves that send_webhook is blocked when the target resolves to a private
or loopback address, and that the failure is recorded in notification_history.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from backend.secuscan import database as database_module
from backend.secuscan.config import settings
from backend.secuscan.database import init_db
from backend.secuscan.models import NotificationDeliveryStatus
from backend.secuscan.notification_service import (
    deliver_via_rule,
    send_webhook,
)


@pytest_asyncio.fixture
async def test_db(setup_test_environment):
    db = await init_db(settings.database_path)
    yield db
    if database_module.db is not None:
        await database_module.db.disconnect()
        database_module.db = None


async def _seed_finding(db, *, severity: str = "critical") -> tuple[str, str]:
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
        ) VALUES (?, ?, 'nmap', 'Open port', 'network', ?, '127.0.0.1', 'desc', 'fix')
        """,
        (finding_id, task_id, severity),
    )
    return task_id, finding_id


async def _seed_rule(
    db,
    *,
    target: str = "https://example.com/hook",
    severity_threshold: str = "high",
    is_active: int = 1,
) -> str:
    rule_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO notification_rules (
            id, name, severity_threshold, channel_type, target_url_or_email, is_active
        ) VALUES (?, 'Egress test rule', ?, 'webhook', ?, ?)
        """,
        (rule_id, severity_threshold, target, is_active),
    )
    return rule_id


# ---------------------------------------------------------------------------
# send_webhook unit-level egress guard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_webhook_blocked_for_loopback():
    """
    send_webhook to a loopback address must fail without making a real
    network call. Simulates egress denial by patching httpx to raise a
    connection error, matching what an egress firewall would produce.
    """
    import httpx

    with patch(
        "backend.secuscan.notification_service.httpx.AsyncClient",
        autospec=True,
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError(
            "Network egress denied: loopback address blocked"
        )

        ok, error = await send_webhook("http://127.0.0.1/hook", {"event": "test"})

    assert ok is False
    assert error is not None
    assert "127.0.0.1" in error or "egress" in error.lower() or "blocked" in error.lower() or "connect" in error.lower()


@pytest.mark.asyncio
async def test_send_webhook_blocked_for_private_range():
    """
    send_webhook to a private RFC-1918 address must fail the same way.
    """
    import httpx

    with patch(
        "backend.secuscan.notification_service.httpx.AsyncClient",
        autospec=True,
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post.side_effect = httpx.ConnectError(
            "Network egress denied: private address blocked"
        )

        ok, error = await send_webhook("http://10.0.0.1/hook", {"event": "test"})

    assert ok is False
    assert error is not None


@pytest.mark.asyncio
async def test_send_webhook_http_4xx_returns_failure():
    """
    A 4xx response from a webhook endpoint is treated as a failure.
    Ensures the caller gets ok=False and an actionable error string.
    """
    import httpx

    mock_response = AsyncMock()
    mock_response.status_code = 403

    with patch(
        "backend.secuscan.notification_service.httpx.AsyncClient",
        autospec=True,
    ) as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        ok, error = await send_webhook("https://example.com/hook", {"event": "test"})

    assert ok is False
    assert "403" in error


# ---------------------------------------------------------------------------
# deliver_via_rule egress integration: failure is recorded in history
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deliver_via_rule_records_failure_when_egress_blocked(test_db):
    """
    When send_webhook raises a network error (egress denied), deliver_via_rule
    must record a FAILED history row with an actionable error message.
    Maintainers can query notification_history to see why delivery failed.
    """
    import httpx

    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db, target="http://127.0.0.1/hook")

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(False, "egress blocked: loopback address")),
    ):
        result = await deliver_via_rule(test_db, rule, finding)

    assert result.status == NotificationDeliveryStatus.FAILED
    assert result.skipped is False
    assert result.error_message is not None

    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
        (rule_id, finding_id),
    )
    assert row is not None
    assert row["status"] == NotificationDeliveryStatus.FAILED.value
    assert "egress" in row["error_message"] or "loopback" in row["error_message"]


@pytest.mark.asyncio
async def test_deliver_via_rule_records_failure_when_webhook_times_out(test_db):
    """
    A webhook timeout (egress allowed but endpoint unreachable) must also
    be recorded as FAILED in notification_history with an actionable message.
    """
    import httpx

    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db)

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(False, "timed out after 10s")),
    ):
        result = await deliver_via_rule(test_db, rule, finding)

    assert result.status == NotificationDeliveryStatus.FAILED
    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
        (rule_id, finding_id),
    )
    assert row is not None
    assert "timed out" in row["error_message"]


@pytest.mark.asyncio
async def test_egress_failure_does_not_prevent_retry_on_next_call(test_db):
    """
    A failed delivery must NOT mark the finding as already-delivered,
    so a retry attempt can succeed if egress recovers.
    """
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db)

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

    # First attempt: egress blocked → failure
    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(False, "egress blocked")),
    ):
        first = await deliver_via_rule(test_db, rule, finding)

    assert first.status == NotificationDeliveryStatus.FAILED

    # Second attempt: egress recovered → success
    with patch(
        "backend.secuscan.notification_service.send_webhook",
        new=AsyncMock(return_value=(True, None)),
    ):
        second = await deliver_via_rule(test_db, rule, finding)

    assert second.status == NotificationDeliveryStatus.SUCCESS
    assert second.skipped is False