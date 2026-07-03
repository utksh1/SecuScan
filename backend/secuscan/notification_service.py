"""
Notification delivery service for high-severity findings.

Evaluates active rules, deduplicates deliveries, redacts alert payloads,
and records outcomes in notification_history. Webhook delivery is live;
email is a logged placeholder until SMTP is added.
"""

from __future__ import annotations

import json
import html
import logging
import socket
import ssl
import uuid
import ipaddress
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from types import TracebackType
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type
from urllib.parse import urlparse

import httpx
import httpcore

from .database import Database
from .models import NotificationChannelType, NotificationDeliveryStatus
from .redaction import redact_dict, redact_inputs

logger = logging.getLogger(__name__)

# Lower rank = more severe. A finding meets the threshold when its rank is
# less than or equal to the rule threshold rank.
_SEVERITY_RANK: Dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
}

_WEBHOOK_TIMEOUT_SECONDS = 10.0
_WEBHOOK_CONNECT_TIMEOUT_SECONDS = 5.0
_USER_AGENT = "SecuScan-Notifications/1.0"

def get_delivery_configuration() -> Dict[str, Any]:
    """Return the currently active configuration for notification delivery."""
    return {
        "webhook_timeout_seconds": _WEBHOOK_TIMEOUT_SECONDS,
        "webhook_connect_timeout_seconds": _WEBHOOK_CONNECT_TIMEOUT_SECONDS,
        "max_retries": 0,
        "backoff_factor_seconds": 0.0,
    }

SOCKET_OPTION = Tuple[int, int, int | bytes]


class _PinnedIPNetworkStream(httpcore.AsyncNetworkStream):
    """Wraps a network stream so that ``start_tls`` always uses the original
    hostname for SNI / certificate verification, even when the TCP connection
    was made to a different (resolved-IP) address."""

    __slots__ = ("_inner", "_original_hostname")

    def __init__(
        self, inner: httpcore.AsyncNetworkStream, original_hostname: str
    ) -> None:
        self._inner = inner
        self._original_hostname = original_hostname

    async def read(self, max_bytes: int, timeout: float | None = None) -> bytes:
        return await self._inner.read(max_bytes, timeout)

    async def write(self, buffer: bytes, timeout: float | None = None) -> None:
        await self._inner.write(buffer, timeout)

    async def aclose(self) -> None:
        await self._inner.aclose()

    async def start_tls(
        self,
        ssl_context: ssl.SSLContext,
        server_hostname: str | None = None,
        timeout: float | None = None,
    ) -> httpcore.AsyncNetworkStream:
        return await self._inner.start_tls(
            ssl_context=ssl_context,
            server_hostname=self._original_hostname,
            timeout=timeout,
        )

    def get_extra_info(self, info: str) -> Any:
        return self._inner.get_extra_info(info)


class _PinnedIPNetworkBackend(httpcore.AsyncNetworkBackend):
    """Network backend that connects TCP to the validated (pinned) IP while
    preserving the original hostname for subsequent TLS negotiation."""

    __slots__ = ("_resolved_ip", "_original_hostname", "_default_backend")

    def __init__(self, resolved_ip: str, original_hostname: str) -> None:
        self._resolved_ip = resolved_ip
        self._original_hostname = original_hostname
        from httpcore._backends.auto import AutoBackend

        self._default_backend = AutoBackend()

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        stream = await self._default_backend.connect_tcp(
            host=self._resolved_ip,
            port=port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )
        return _PinnedIPNetworkStream(stream, self._original_hostname)

    async def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        return await self._default_backend.connect_unix_socket(
            path, timeout, socket_options
        )

    async def sleep(self, seconds: float) -> None:
        await self._default_backend.sleep(seconds)


class _PinnedIPTransport(httpx.AsyncBaseTransport):
    """httpx transport that wraps an ``httpcore.AsyncConnectionPool`` using a
    ``_PinnedIPNetworkBackend`` so that every outgoing connection is pinned to a
    pre-validated IP address while the original hostname is used for TLS."""

    __slots__ = ("_pool",)

    def __init__(self, resolved_ip: str, original_hostname: str) -> None:
        import httpcore as _httpcore

        backend = _PinnedIPNetworkBackend(resolved_ip, original_hostname)
        self._pool = _httpcore.AsyncConnectionPool(network_backend=backend)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        import httpcore as _httpcore

        req = _httpcore.Request(
            method=request.method,
            url=_httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        resp = await self._pool.handle_async_request(req)
        content = b""
        async for chunk in resp.stream:
            content += chunk
        return httpx.Response(
            status_code=resp.status,
            headers=resp.headers,
            content=content,
            extensions=resp.extensions,
        )

    async def __aenter__(self) -> _PinnedIPTransport:
        await self._pool.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] | None = None,
        exc_value: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        await self._pool.__aexit__(exc_type, exc_value, traceback)

    async def aclose(self) -> None:
        await self._pool.aclose()


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of a single rule delivery attempt for one finding."""

    rule_id: str
    finding_id: str
    status: NotificationDeliveryStatus
    skipped: bool = False
    error_message: Optional[str] = None


class NotificationRuleConflictError(Exception):
    """Raised when a notification rule update loses an optimistic lock race."""

    def __init__(self, current_rule: Dict[str, Any]) -> None:
        super().__init__("Notification rule was updated by another request")
        self.current_rule = current_rule


def severity_meets_threshold(finding_severity: str, rule_threshold: str) -> bool:
    """Return True when finding severity is at or above the rule threshold."""
    finding_rank = _SEVERITY_RANK.get(str(finding_severity).lower())
    threshold_rank = _SEVERITY_RANK.get(str(rule_threshold).lower())
    if finding_rank is None or threshold_rank is None:
        return False
    return finding_rank <= threshold_rank


def build_alert_payload(
    finding: Dict[str, Any],
    rule: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a redacted JSON-serializable alert payload for outbound channels."""
    metadata: Dict[str, Any] = {}
    raw_metadata = finding.get("metadata_json")
    if raw_metadata:
        try:
            parsed = json.loads(raw_metadata)
            if isinstance(parsed, dict):
                metadata = redact_inputs(parsed)
        except (TypeError, json.JSONDecodeError):
            metadata = {"raw": str(raw_metadata)}

    payload = {
        "event": "finding.alert",
        "rule": {
            "id": rule.get("id"),
            "name": rule.get("name"),
            "severity_threshold": rule.get("severity_threshold"),
            "channel_type": rule.get("channel_type"),
        },
        "finding": {
            "id": finding.get("id"),
            "task_id": finding.get("task_id"),
            "plugin_id": finding.get("plugin_id"),
            "title": finding.get("title"),
            "category": finding.get("category"),
            "severity": finding.get("severity"),
            "target": finding.get("target"),
            "description": finding.get("description"),
            "remediation": finding.get("remediation"),
            "metadata": metadata,
        },
    }
    return redact_dict(payload)


async def was_already_delivered(
    db: Database,
    rule_id: str,
    finding_id: str,
) -> bool:
    """Return True when this rule already successfully notified this finding."""
    row = await db.fetchone(
        """
        SELECT id FROM notification_history
        WHERE rule_id = ? AND finding_id = ? AND status = ?
        LIMIT 1
        """,
        (rule_id, finding_id, NotificationDeliveryStatus.SUCCESS.value),
    )
    return row is not None


async def record_delivery(
    db: Database,
    rule_id: str,
    finding_id: str,
    status: NotificationDeliveryStatus,
    error_message: Optional[str] = None,
) -> str:
    """Persist a delivery attempt and return the history row id."""
    history_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO notification_history (id, rule_id, finding_id, status, error_message)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            history_id,
            rule_id,
            finding_id,
            status.value,
            error_message,
        ),
    )
    return history_id


async def send_webhook(
    target_url: str, payload: Dict[str, Any]
) -> tuple[bool, Optional[str]]:
    """POST a redacted alert payload to a webhook URL with SSRF protections.

    Always resolves the target hostname and validates every returned IP against
    the configured SECUSCAN_NOTIFICATION_BLOCKED_IP_RANGES, independent of the
    general enforce_network_policy setting.

    The address actually contacted is the validated IP (not the hostname) to
    prevent DNS-rebinding / TOCTOU attacks.  How this is achieved differs by
    scheme so that TLS verification is not broken:

    * **http**: the URL is rewritten to the resolved IP and the ``Host`` header
      is set to the original hostname.  Plain HTTP has no TLS so there is no
      certificate-verification concern.

    * **https**: a custom ``_PinnedIPTransport`` binds the TCP connection to the
      validated IP while the original hostname is preserved for TLS SNI and
      certificate verification, keeping the original hostname in the URL.
    """
    from .config import settings
    from urllib.parse import urlparse, urlunparse

    parsed = urlparse(target_url)
    hostname = parsed.hostname
    if not hostname:
        return False, "Webhook URL has no hostname"

    # Resolve and validate every address the hostname may return.
    try:
        addrs = socket.getaddrinfo(
            hostname, parsed.port or 443, proto=socket.IPPROTO_TCP
        )
    except OSError:
        return False, "Webhook URL hostname could not be resolved"

    validated_ips: list[str] = []
    for family, _stype, _proto, _cname, sockaddr in addrs:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        blocked = False
        for blocked_cidr in settings.notification_blocked_ip_ranges:
            try:
                if ip in ipaddress.ip_network(blocked_cidr, strict=False):
                    blocked = True
                    break
            except ValueError:
                continue
        if blocked:
            return False, f"Webhook target resolves to blocked IP range: {blocked_cidr}"
        validated_ips.append(ip_str)

    if not validated_ips:
        return False, "Webhook URL did not resolve to any valid IP addresses"

    timeout = httpx.Timeout(
        timeout=_WEBHOOK_TIMEOUT_SECONDS,
        connect=_WEBHOOK_CONNECT_TIMEOUT_SECONDS,
    )

    resolved_ip = validated_ips[0]
    scheme = parsed.scheme

    # -- Build the request URL and choose the pinning strategy --------------
    if scheme == "https":
        # Use a custom transport that connects to the pinned IP while keeping
        # the original hostname for TLS SNI and certificate verification.
        transport = _PinnedIPTransport(resolved_ip, hostname)
        request_url = target_url
        extra_headers: dict[str, str] = {}
    else:
        # Rewrite the URL to the resolved IP and set the Host header.
        # This is safe for plain HTTP because there is no TLS handshake.
        new_netloc = f"[{resolved_ip}]" if ":" in resolved_ip else resolved_ip
        if parsed.port:
            new_netloc = f"{new_netloc}:{parsed.port}"
        request_url = urlunparse(
            (
                scheme,
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )
        transport = None
        extra_headers = {"Host": hostname}

    try:
        client_kwargs: dict[str, Any] = {
            "timeout": timeout,
            "follow_redirects": False,
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        async with httpx.AsyncClient(**client_kwargs) as client:
            headers = {
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            }
            headers.update(extra_headers)
            response = await client.post(
                request_url,
                json=payload,
                headers=headers,
            )

        if response.status_code >= 400:
            return False, f"Webhook returned HTTP {response.status_code}"

        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("location", "")
            if redirect_url:
                from urllib.parse import urlparse

                parsed_redirect = urlparse(redirect_url)
                if parsed_redirect.hostname:
                    try:
                        redirect_ips = socket.getaddrinfo(
                            parsed_redirect.hostname, parsed_redirect.port or 443
                        )
                        for _family, _stype, _proto, _cname, sockaddr in redirect_ips:
                            rip = ipaddress.ip_address(sockaddr[0])
                            for blocked_cidr in settings.notification_blocked_ip_ranges:
                                try:
                                    if rip in ipaddress.ip_network(
                                        blocked_cidr, strict=False
                                    ):
                                        return (
                                            False,
                                            f"Redirect to blocked IP range: {blocked_cidr}",
                                        )
                                except ValueError:
                                    continue
                    except OSError:
                        return (
                            False,
                            f"Could not resolve redirect target: {redirect_url}",
                        )

        return True, None
    except httpx.HTTPError as exc:
        return False, str(exc)
    except OSError as exc:
        return False, str(exc)


def _send_smtp_email_sync(
    target_email: str,
    subject: str,
    body_text: str,
    body_html: str,
) -> None:
    """Synchronously send an email using settings SMTP parameters."""
    from .config import settings

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email
    msg["To"] = target_email

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10.0) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, [target_email], msg.as_string())


async def send_email(
    target_email: str,
    payload: Dict[str, Any],
) -> tuple[bool, Optional[str]]:
    """Send a rich SMTP email notification containing finding details asynchronously."""
    from .config import settings

    finding = payload.get("finding", {})
    finding_id = finding.get("id")

    if not settings.smtp_username or not settings.smtp_password:
        logger.info(
            "SMTP credentials not configured. Skipping email delivery (Logged placeholder): target=%s finding_id=%s",
            target_email,
            finding_id,
        )
        return True, None

    subject = f"[SecuScan Alert] {finding.get('severity', 'INFO').upper()} vulnerability detected on {finding.get('target')}"

    body_text = (
        f"SecuScan Security Alert\n"
        f"=======================\n\n"
        f"A vulnerability has been identified during a scan run:\n\n"
        f"Title: {finding.get('title')}\n"
        f"Category: {finding.get('category')}\n"
        f"Severity: {finding.get('severity')}\n"
        f"Target: {finding.get('target')}\n\n"
        f"Description:\n{finding.get('description')}\n\n"
        f"Remediation Guidance:\n{finding.get('remediation')}\n\n"
        f"View results in the SecuScan Dashboard."
    )

    title_esc = html.escape(str(finding.get('title') or ""))
    category_esc = html.escape(str(finding.get('category') or ""))
    severity_esc = html.escape(str(finding.get('severity') or ""))
    target_esc = html.escape(str(finding.get('target') or ""))
    description_esc = html.escape(str(finding.get('description') or "")).replace('\n', '<br>')
    remediation_esc = html.escape(str(finding.get('remediation') or "")).replace('\n', '<br>')

    body_html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #0f172a; max-width: 600px; margin: 0 auto; padding: 20px;">
  <h2 style="color: #991b1b; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">🛡️ SecuScan Alert</h2>
  <p>A new high-priority security vulnerability has been identified:</p>
  <table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
    <tr style="background-color: #f8fafc;">
      <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold; width: 140px;">Title</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0;">{title_esc}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Category</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0;">{category_esc}</td>
    </tr>
    <tr style="background-color: #f8fafc;">
      <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Severity</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0; text-transform: uppercase; font-weight: bold; color: #991b1b;">{severity_esc}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: bold;">Target</td>
      <td style="padding: 10px; border: 1px solid #e2e8f0;">{target_esc}</td>
    </tr>
  </table>
  <h3>Description</h3>
  <p style="color: #475569; background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0;">{description_esc}</p>
  <h3>Remediation Guidance</h3>
  <p style="color: #166534; background-color: #f0fdf4; padding: 15px; border-radius: 8px; border: 1px solid #bbf7d0; border-left: 4px solid #22c55e;">
    {remediation_esc}
  </p>
  <p style="font-size: 11px; color: #64748b; margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px;">
    This is an automated notification from your SecuScan installation.
  </p>
</body>
</html>"""

    try:
        await asyncio.to_thread(_send_smtp_email_sync, target_email, subject, body_text, body_html)
        return True, None
    except Exception as exc:
        logger.error("Failed to send SMTP email notification to %s: %s", target_email, exc)
        return False, str(exc)


async def deliver_via_rule(
    db: Database,
    rule: Dict[str, Any],
    finding: Dict[str, Any],
) -> DeliveryResult:
    """Attempt delivery for one rule/finding pair."""
    rule_id = str(rule["id"])
    finding_id = str(finding["id"])

    if not bool(rule.get("is_active")):
        return DeliveryResult(
            rule_id=rule_id,
            finding_id=finding_id,
            status=NotificationDeliveryStatus.FAILED,
            skipped=True,
            error_message="Rule is inactive",
        )

    if not severity_meets_threshold(
        str(finding.get("severity", "info")),
        str(rule.get("severity_threshold", "info")),
    ):
        return DeliveryResult(
            rule_id=rule_id,
            finding_id=finding_id,
            status=NotificationDeliveryStatus.FAILED,
            skipped=True,
            error_message="Finding severity below rule threshold",
        )

    if await was_already_delivered(db, rule_id, finding_id):
        return DeliveryResult(
            rule_id=rule_id,
            finding_id=finding_id,
            status=NotificationDeliveryStatus.SUCCESS,
            skipped=True,
            error_message="Already delivered",
        )

    payload = build_alert_payload(finding, rule)
    channel = str(rule.get("channel_type", "")).lower()
    target = str(rule.get("target_url_or_email", ""))

    if channel == NotificationChannelType.WEBHOOK.value:
        ok, error = await send_webhook(target, payload)
    elif channel == NotificationChannelType.EMAIL.value:
        ok, error = await send_email(target, payload)
    else:
        ok, error = False, f"Unsupported channel type: {channel}"

    status = (
        NotificationDeliveryStatus.SUCCESS if ok else NotificationDeliveryStatus.FAILED
    )
    await record_delivery(db, rule_id, finding_id, status, error)

    return DeliveryResult(
        rule_id=rule_id,
        finding_id=finding_id,
        status=status,
        error_message=error,
    )


async def process_finding_notifications(
    db: Database,
    finding_id: str,
) -> List[DeliveryResult]:
    """Evaluate all active rules against one finding and attempt delivery."""
    finding = await db.fetchone("SELECT * FROM findings WHERE id = ?", (finding_id,))
    if not finding:
        return []

    rules = await db.fetchall(
        "SELECT * FROM notification_rules WHERE is_active = 1 ORDER BY created_at ASC"
    )
    results: List[DeliveryResult] = []
    for rule in rules:
        results.append(await deliver_via_rule(db, rule, finding))
    return results


async def process_task_notifications(
    db: Database,
    task_id: str,
) -> List[DeliveryResult]:
    """Evaluate notifications for every finding produced by a task."""
    findings = await db.fetchall(
        "SELECT id FROM findings WHERE task_id = ? ORDER BY discovered_at ASC",
        (task_id,),
    )
    results: List[DeliveryResult] = []
    for row in findings:
        results.extend(await process_finding_notifications(db, str(row["id"])))
    return results


async def update_notification_rule(
    db: Database,
    *,
    current_rule: Dict[str, Any],
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply an optimistic-lock update to a notification rule row."""
    assignments = [f"{column} = ?" for column in updates]
    params = list(updates.values())
    assignments.append("updated_at = strftime('%Y-%m-%d %H:%M:%f', 'now')")
    params.extend((current_rule["id"], current_rule["updated_at"]))

    cursor = await db.execute(
        f"""
        UPDATE notification_rules
        SET {', '.join(assignments)}
        WHERE id = ? AND updated_at = ?
        """,
        tuple(params),
    )
    if cursor.rowcount == 0:
        latest = await db.fetchone(
            "SELECT * FROM notification_rules WHERE id = ?",
            (current_rule["id"],),
        )
        if latest is None:
            raise KeyError(current_rule["id"])
        raise NotificationRuleConflictError(latest)

    updated = await db.fetchone(
        "SELECT * FROM notification_rules WHERE id = ?",
        (current_rule["id"],),
    )
    if updated is None:
        raise KeyError(current_rule["id"])
    return updated


async def process_slack_notification(db: Database, task_id: str) -> None:
    """Send a structured JSON payload and a clean block message to the configured Slack Webhook after scan completion."""
    from .config import settings

    webhook_url = settings.slack_webhook_url
    if not webhook_url:
        return

    # Fetch task details
    task = await db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
    if not task:
        logger.warning("Slack notification: Task %s not found in database", task_id)
        return

    status = str(task.get("status") or "unknown").upper()
    tool_name = task.get("tool_name") or task.get("plugin_id") or "Security Scan"
    target = task.get("target") or "Unknown Target"
    duration = task.get("duration_seconds")
    duration_str = f"{duration:.2f}s" if duration is not None else "N/A"

    # Fetch findings to count and build severity breakdown
    findings = await db.fetchall(
        "SELECT severity FROM findings WHERE task_id = ?",
        (task_id,),
    )
    total_findings = len(findings)
    
    severity_counts: Dict[str, int] = {}
    for row in findings:
        sev = str(row.get("severity") or "info").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Formulate severity breakdown message
    severity_lines = []
    for sev in ["critical", "high", "medium", "low", "info"]:
        count = severity_counts.get(sev, 0)
        if count > 0 or sev in ["critical", "high", "medium"]:
            severity_lines.append(f"• *{sev.capitalize()}:* {count}")
    severity_text = "\n".join(severity_lines)

    # Status-specific formatting
    status_icon = "✅" if status == "COMPLETED" else "❌" if status == "FAILED" else "ℹ️"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_icon} SecuScan: Scan {status.capitalize()}",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Tool:*\n{tool_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Target:*\n{target}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Status:*\n{status}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Duration:*\n{duration_str}"
                }
            ]
        }
    ]

    if status == "FAILED" and task.get("error_message"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Error Message:*\n{task.get('error_message')}"
            }
        })
    else:
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Total Findings:*\n{total_findings}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Severity Breakdown:*\n{severity_text}"
                }
            ]
        })

    payload = {
        "text": f"SecuScan scan of {target} finished with status: {status}",
        "blocks": blocks,
        "scan_data": {
            "task_id": task_id,
            "tool_name": tool_name,
            "target": target,
            "status": status.lower(),
            "duration_seconds": duration,
            "total_findings": total_findings,
            "severity_counts": severity_counts,
            "error_message": task.get("error_message")
        }
    }

    try:
        ok, error = await send_webhook(webhook_url, payload)
        if ok:
            logger.info("Slack notification for task %s sent successfully", task_id)
        else:
            logger.warning("Failed to send Slack notification for task %s: %s", task_id, error)
    except Exception as exc:
        logger.error("Error sending Slack notification for task %s: %s", task_id, exc, exc_info=True)
