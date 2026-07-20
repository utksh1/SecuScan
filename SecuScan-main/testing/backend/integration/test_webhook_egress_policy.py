"""
Regression guard: webhook delivery must respect network egress controls.

Asserts the *real* SSRF protection path in send_webhook — DNS resolution
plus validation of every resolved IP against
settings.notification_blocked_ip_ranges — actually blocks loopback and
link-local/metadata destinations before any HTTP request is attempted.
No httpx mocking for the blocking assertions: the policy check runs
before httpx is ever touched, so these tests exercise the real code path.
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
# Real egress policy path: no httpx mocking, asserts the actual IP-range
# check against settings.notification_blocked_ip_ranges.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_webhook_blocks_loopback_via_real_dns_resolution():
    """
    'localhost' resolves to 127.0.0.1, which is in the default
    notification_blocked_ip_ranges (127.0.0.0/8). send_webhook must reject
    it during DNS/IP validation, before httpx is ever invoked.
    """
    ok, error = await send_webhook("http://localhost:9/hook", {"event": "test"})

    assert ok is False
    assert error is not None
    assert "blocked" in error.lower() or "resolve" in error.lower()


@pytest.mark.asyncio
async def test_send_webhook_blocks_literal_loopback_ip():
    """
    A literal loopback IP in the URL must also be blocked — confirms the
    check applies to the resolved/parsed IP, not just hostnames that
    require a DNS lookup.
    """
    ok, error = await send_webhook("http://127.0.0.1:9/hook", {"event": "test"})

    assert ok is False
    assert error is not None
    assert "blocked" in error.lower()
    assert "127.0.0" in error


@pytest.mark.asyncio
async def test_send_webhook_blocks_link_local_metadata_address():
    """
    The cloud metadata endpoint 169.254.169.254 is explicitly listed in
    notification_blocked_ip_ranges. This guards against SSRF attacks that
    try to exfiltrate cloud instance credentials via a webhook rule.
    """
    ok, error = await send_webhook("http://169.254.169.254/hook", {"event": "test"})

    assert ok is False
    assert error is not None
    assert "blocked" in error.lower()


@pytest.mark.asyncio
async def test_send_webhook_rejects_url_with_no_hostname():
    """A malformed webhook URL with no hostname fails cleanly, pre-DNS."""
    ok, error = await send_webhook("not-a-url", {"event": "test"})

    assert ok is False
    assert "hostname" in error.lower()


# ---------------------------------------------------------------------------
# deliver_via_rule integration: the real block surfaces as a FAILED history
# row with an actionable message, end to end, no mocking of send_webhook.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deliver_via_rule_records_failure_for_loopback_target(test_db):
    """
    End-to-end: a rule configured with a loopback target must fail via the
    real SSRF check inside send_webhook, and that failure must be recorded
    in notification_history with the blocking reason — no send_webhook
    mocking, so this proves the policy check is actually wired in.
    """
    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db, target="http://127.0.0.1:9/hook")

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    result = await deliver_via_rule(test_db, rule, finding)

    assert result.status == NotificationDeliveryStatus.FAILED
    assert result.skipped is False
    assert result.error_message is not None
    assert "blocked" in result.error_message.lower()

    row = await test_db.fetchone(
        "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
        (rule_id, finding_id),
    )
    assert row is not None
    assert row["status"] == NotificationDeliveryStatus.FAILED.value
    assert "blocked" in row["error_message"].lower()


@pytest.mark.asyncio
async def test_egress_block_does_not_mark_finding_as_delivered(test_db):
    """
    A blocked delivery must not be treated as a successful delivery —
    was_already_delivered must stay False so a corrected rule can retry.
    """
    from backend.secuscan.notification_service import was_already_delivered

    _, finding_id = await _seed_finding(test_db)
    rule_id = await _seed_rule(test_db, target="http://127.0.0.1:9/hook")

    finding = await test_db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    rule = await test_db.fetchone("SELECT * FROM notification_rules WHERE id = ?", (rule_id,))

    await deliver_via_rule(test_db, rule, finding)

    assert await was_already_delivered(test_db, rule_id, finding_id) is False


# ---------------------------------------------------------------------------
# Legitimate target still works: real network call is mocked at the httpx
# layer only (after IP validation has already passed), proving the policy
# check doesn't false-positive on allowed destinations.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_webhook_allows_non_blocked_target():
    """
    A target that resolves to a public, non-blocked IP must pass the
    egress check and reach the HTTP layer, where we mock only the
    final response — proving the policy check doesn't over-block.
    """
    with patch(
        "backend.secuscan.notification_service.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("93.184.216.34", 443))],
    ):
        mock_response = AsyncMock()
        mock_response.status_code = 200
        with patch(
            "backend.secuscan.notification_service.httpx.AsyncClient",
            autospec=True,
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            ok, error = await send_webhook("https://example.com/hook", {"event": "test"})

    assert ok is True
    assert error is None