import json
import socket
import ssl
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

    finding = await test_db.fetchone(
        "SELECT * FROM findings WHERE id = ?", (finding_id,)
    )
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

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

    finding = await test_db.fetchone(
        "SELECT * FROM findings WHERE id = ?", (finding_id,)
    )
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

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

    finding = await test_db.fetchone(
        "SELECT * FROM findings WHERE id = ?", (finding_id,)
    )
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

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

    finding = await test_db.fetchone(
        "SELECT * FROM findings WHERE id = ?", (finding_id,)
    )
    rule = await test_db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?", (rule_id,)
    )

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

    def fake_success_addr(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    with (
        patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)),
        patch(
            "backend.secuscan.notification_service.socket.getaddrinfo",
            side_effect=fake_success_addr,
        ),
    ):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_send_webhook_http_error():
    """Webhook returning >=400 is reported as failure."""
    from backend.secuscan.notification_service import send_webhook

    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_post = AsyncMock(return_value=mock_response)

    def fake_success_addr(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    with (
        patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)),
        patch(
            "backend.secuscan.notification_service.socket.getaddrinfo",
            side_effect=fake_success_addr,
        ),
    ):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is False
    assert "500" in err


@pytest.mark.asyncio
async def test_send_webhook_http_exception():
    """Transport-level errors are caught and returned as failure."""
    from backend.secuscan.notification_service import send_webhook

    mock_post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

    def fake_success_addr(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    with (
        patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)),
        patch(
            "backend.secuscan.notification_service.socket.getaddrinfo",
            side_effect=fake_success_addr,
        ),
    ):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is False
    assert "Connection refused" in err


@pytest.mark.asyncio
async def test_send_webhook_blocks_private_ip_resolution(monkeypatch):
    """Webhook to a hostname that resolves to a private IP must be rejected."""
    from backend.secuscan.notification_service import send_webhook

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("10.0.0.5", 443))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )
    ok, err = await send_webhook("https://internal.example.com/hook", {"event": "test"})
    assert ok is False
    assert "blocked" in err.lower()


@pytest.mark.asyncio
async def test_send_webhook_pins_connection_ip_for_https(monkeypatch):
    """HTTPS webhook keeps the original hostname in the URL so that TLS SNI
    and certificate verification operate against the expected name. The IP
    pinning is done inside the custom transport, not via URL rewriting."""
    from backend.secuscan.notification_service import send_webhook

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_post = AsyncMock(return_value=mock_response)
    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_cm):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is True
    call_args, call_kwargs = mock_post.call_args
    posted_url = str(call_args[0]) if call_args else ""
    # HTTPS must NOT rewrite the URL to the IP — doing so would break TLS.
    assert "hooks.example.com" in posted_url, "HTTPS URL must keep original hostname"
    assert "93.184.216.34" not in posted_url, (
        "HTTPS URL must NOT contain the resolved IP"
    )


@pytest.mark.asyncio
async def test_send_webhook_pins_connection_ip_for_http(monkeypatch):
    """HTTP webhook rewrites the URL to the resolved IP and sets the Host
    header. There is no TLS, so this is safe and prevents DNS rebinding."""
    from backend.secuscan.notification_service import send_webhook

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 80))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_post = AsyncMock(return_value=mock_response)
    mock_client = AsyncMock()
    mock_client.post = mock_post
    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_client

    with patch("httpx.AsyncClient", return_value=mock_cm):
        ok, err = await send_webhook(
            "http://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is True
    call_args, call_kwargs = mock_post.call_args
    posted_url = str(call_args[0]) if call_args else ""
    assert "93.184.216.34" in posted_url, (
        "HTTP request must go to resolved IP, not hostname"
    )
    headers = call_kwargs.get("headers", {})
    assert headers.get("Host") == "hooks.example.com"


@pytest.mark.asyncio
async def test_send_webhook_blocks_metadata_ip_resolution(monkeypatch):
    """Webhook to a hostname resolving to metadata IP must be rejected."""
    from backend.secuscan.notification_service import send_webhook

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("169.254.169.254", 80))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )
    ok, err = await send_webhook("http://metadata.example.com/hook", {"event": "test"})
    assert ok is False
    assert "blocked" in err.lower()


@pytest.mark.asyncio
async def test_send_webhook_rejects_unresolvable_hostname(monkeypatch):
    """Unresolvable webhook hostname is reported as failure."""
    from backend.secuscan.notification_service import send_webhook

    def fake_getaddrinfo(*args, **kwargs):
        raise OSError("Name or service not known")

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )
    ok, err = await send_webhook(
        "https://nonexistent.example.invalid/hook", {"event": "test"}
    )
    assert ok is False
    assert "could not be resolved" in err.lower()


@pytest.mark.asyncio
async def test_send_webhook_ssrf_independent_of_enforce_network_policy(monkeypatch):
    """SSRF protection must work even when enforce_network_policy is False."""
    from backend.secuscan.notification_service import send_webhook
    from backend.secuscan.config import settings

    monkeypatch.setattr(settings, "enforce_network_policy", False)

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("10.0.0.5", 443))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )
    ok, err = await send_webhook("https://internal.example.com/hook", {"event": "test"})
    assert ok is False
    assert "blocked" in err.lower()


@pytest.mark.asyncio
async def test_send_webhook_https_uses_pinned_ip_transport(monkeypatch):
    """HTTPS delivery creates _PinnedIPTransport with the validated IP and original hostname."""
    from backend.secuscan.notification_service import send_webhook, _PinnedIPTransport

    transport_args = {}

    def capture_transport(resolved_ip, original_hostname):
        transport_args["resolved_ip"] = resolved_ip
        transport_args["original_hostname"] = original_hostname
        return _PinnedIPTransport(resolved_ip, original_hostname)

    monkeypatch.setattr(
        "backend.secuscan.notification_service._PinnedIPTransport",
        capture_transport,
    )

    def fake_getaddrinfo(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_getaddrinfo
    )

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_post = AsyncMock(return_value=mock_response)

    with patch(
        "httpx.AsyncClient",
        return_value=AsyncMock(
            **{
                "post.return_value": mock_response,
                "__aenter__.return_value.post.return_value": mock_response,
            }
        ),
    ):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is True
    assert transport_args.get("resolved_ip") == "93.184.216.34"
    assert transport_args.get("original_hostname") == "hooks.example.com"


@pytest.mark.asyncio
async def test_send_webhook_redirect_to_blocked_ip():
    """Redirect to a private IP (SSRF) is rejected after delivery."""
    from backend.secuscan.notification_service import send_webhook

    mock_response = AsyncMock()
    mock_response.status_code = 302
    mock_response.headers = {"location": "http://10.0.0.1/evil"}
    mock_post = AsyncMock(return_value=mock_response)

    def fake_getaddrinfo(hostname, port=None, *args, **kwargs):
        if "hooks.example.com" in hostname:
            return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]
        # Redirect target resolves to private IP
        return [(socket.AF_INET, None, None, None, ("10.0.0.1", 80))]

    with (
        patch("httpx.AsyncClient", return_value=_mock_async_client(mock_post)),
        patch(
            "backend.secuscan.notification_service.socket.getaddrinfo",
            side_effect=fake_getaddrinfo,
        ),
    ):
        ok, err = await send_webhook(
            "https://hooks.example.com/alert", {"event": "test"}
        )

    assert ok is False
    assert "blocked" in err.lower()


@pytest.mark.asyncio
async def test_send_webhook_https_delivery_pins_ip_and_preserves_tls_hostname(
    monkeypatch,
):
    """HTTPS webhook delivery through send_webhook connects TCP to the
    validated (pinned) IP address while preserving the original hostname for
    TLS SNI and certificate verification.

    This proves the full SSRF-prevention guarantee end-to-end: DNS resolution,
    IP validation, custom transport creation, TCP-level IP pinning, and
    hostname preservation for the TLS handshake.
    """
    import httpcore._backends.auto as auto_backend
    from backend.secuscan.notification_service import send_webhook

    tcp_connected_to = None
    tls_sni_hostname = None

    class _TLSStream:
        def __init__(self):
            self._buffer = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Length: 0\r\n"
                b"Connection: close\r\n"
                b"\r\n"
            )

        async def read(self, max_bytes, timeout=None):
            if not self._buffer:
                return b""
            chunk = self._buffer[:max_bytes]
            self._buffer = self._buffer[max_bytes:]
            return chunk

        async def write(self, buffer, timeout=None):
            pass

        async def aclose(self):
            pass

        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            nonlocal tls_sni_hostname
            tls_sni_hostname = server_hostname
            return self

        def get_extra_info(self, info):
            return None

    async def _tracking_connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        nonlocal tcp_connected_to
        tcp_connected_to = host
        return _TLSStream()

    monkeypatch.setattr(
        auto_backend.AutoBackend, "connect_tcp", _tracking_connect_tcp
    )

    def fake_resolve(*args, **kwargs):
        return [(socket.AF_INET, None, None, None, ("93.184.216.34", 443))]

    monkeypatch.setattr(
        "backend.secuscan.notification_service.socket.getaddrinfo", fake_resolve
    )

    ok, err = await send_webhook(
        "https://hooks.example.com/alert", {"event": "test"}
    )

    assert ok is True
    assert err is None
    assert tcp_connected_to == "93.184.216.34", (
        f"TCP must connect to validated/pinned IP (93.184.216.34), got {tcp_connected_to!r}"
    )
    assert tls_sni_hostname == "hooks.example.com", (
        f"TLS SNI must use original hostname (hooks.example.com), got {tls_sni_hostname!r}"
    )


@pytest.mark.asyncio
async def test_pinned_ip_network_backend_pins_ip_and_preserves_tls_hostname(
    monkeypatch,
):
    """Regression test: _PinnedIPNetworkBackend connects TCP to the validated
    (pinned) IP address, and _PinnedIPNetworkStream forces the original
    hostname into start_tls for SNI / certificate verification.

    This is the core guarantee that prevents DNS-rebinding / TOCTOU attacks
    without breaking HTTPS hostname verification.
    """
    from backend.secuscan.notification_service import _PinnedIPNetworkBackend

    connected_host = None
    tls_hostname = None

    class TrackingStream:
        async def read(self, max_bytes, timeout=None):
            return b""

        async def write(self, buffer, timeout=None):
            pass

        async def aclose(self):
            pass

        async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
            nonlocal tls_hostname
            tls_hostname = server_hostname
            return self

        def get_extra_info(self, info):
            return None

    import httpcore._backends.auto as auto_backend

    async def tracking_connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        nonlocal connected_host
        connected_host = host
        return TrackingStream()

    monkeypatch.setattr(auto_backend.AutoBackend, "connect_tcp", tracking_connect_tcp)

    backend = _PinnedIPNetworkBackend(
        resolved_ip="93.184.216.34",
        original_hostname="hooks.example.com",
    )

    stream = await backend.connect_tcp(host="hooks.example.com", port=443)

    assert connected_host == "93.184.216.34", (
        f"TCP must connect to pinned IP (93.184.216.34), got {connected_host!r}"
    )

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    await stream.start_tls(
        ssl_context=ssl_ctx,
        server_hostname="this-should-be-overridden.com",
    )

    assert tls_hostname == "hooks.example.com", (
        f"TLS SNI must use original hostname (hooks.example.com), got {tls_hostname!r}"
    )


@pytest.mark.asyncio
async def test_process_slack_notification_success(test_db, monkeypatch):
    """process_slack_notification compiles task info, counts findings, and sends webhook successfully."""
    task_id, finding_id = await _seed_finding(test_db, severity="high")
    
    monkeypatch.setattr(settings, "slack_webhook_url", "https://slack.example.invalid/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX")

    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.secuscan.notification_service.send_webhook", mock_send)

    from backend.secuscan.notification_service import process_slack_notification
    await process_slack_notification(test_db, task_id)

    assert mock_send.call_count == 1
    call_args, _ = mock_send.call_args
    target_url = call_args[0]
    payload = call_args[1]

    assert target_url == "https://slack.example.invalid/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX"
    assert "blocks" in payload
    assert len(payload["blocks"]) >= 3
    assert "High" in payload["blocks"][2]["fields"][1]["text"]
    assert "Total Findings" in payload["blocks"][2]["fields"][0]["text"]


@pytest.mark.asyncio
async def test_process_slack_notification_failed_task(test_db, monkeypatch):
    """process_slack_notification sends error details when status is FAILED."""
    task_id = str(uuid.uuid4())
    await test_db.execute(
        """
        INSERT INTO tasks (
            id, plugin_id, tool_name, target, status, inputs_json, consent_granted, error_message
        ) VALUES (?, 'nmap', 'nmap', '127.0.0.1', 'failed', '{}', 1, 'Connection refused')
        """,
        (task_id,),
    )
    
    monkeypatch.setattr(settings, "slack_webhook_url", "https://slack.example.invalid/services/test")
    mock_send = AsyncMock(return_value=(True, None))
    monkeypatch.setattr("backend.secuscan.notification_service.send_webhook", mock_send)

    from backend.secuscan.notification_service import process_slack_notification
    await process_slack_notification(test_db, task_id)

    assert mock_send.call_count == 1
    call_args, _ = mock_send.call_args
    payload = call_args[1]

    assert "blocks" in payload
    assert "Error Message" in payload["blocks"][2]["text"]["text"]
    assert "Connection refused" in payload["blocks"][2]["text"]["text"]
