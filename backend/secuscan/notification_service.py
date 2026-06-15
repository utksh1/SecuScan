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
import uuid
import ipaddress
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

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


@dataclass(frozen=True)
class DeliveryResult:
    """Outcome of a single rule delivery attempt for one finding."""

    rule_id: str
    finding_id: str
    status: NotificationDeliveryStatus
    skipped: bool = False
    error_message: Optional[str] = None


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


async def send_webhook(target_url: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """POST a redacted alert payload to a webhook URL with SSRF protections."""
    from .config import settings

    timeout = httpx.Timeout(
        timeout=_WEBHOOK_TIMEOUT_SECONDS,
        connect=_WEBHOOK_CONNECT_TIMEOUT_SECONDS,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(
                target_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": _USER_AGENT,
                },
            )

        if response.status_code >= 400:
            return False, f"Webhook returned HTTP {response.status_code}"

        if response.status_code in (301, 302, 303, 307, 308):
            redirect_url = response.headers.get("location", "")
            if redirect_url:
                from urllib.parse import urlparse
                parsed = urlparse(redirect_url)
                if parsed.hostname:
                    try:
                        redirect_ips = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
                        for _family, _stype, _proto, _cname, sockaddr in redirect_ips:
                            rip = ipaddress.ip_address(sockaddr[0])
                            for blocked_cidr in settings.notification_blocked_ip_ranges:
                                try:
                                    if rip in ipaddress.ip_network(blocked_cidr, strict=False):
                                        return False, f"Redirect to blocked IP range: {blocked_cidr}"
                                except ValueError:
                                    continue
                    except OSError:
                        return False, f"Could not resolve redirect target: {redirect_url}"

        return True, None
    except httpx.HTTPError as exc:
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
