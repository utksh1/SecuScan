"""
Notification delivery service for high-severity findings.

Evaluates active rules, deduplicates deliveries, redacts alert payloads,
and records outcomes in notification_history. Webhook delivery is live;
email is a logged placeholder until SMTP is added.
"""

from __future__ import annotations

import json
import logging
import socket
import uuid
import ipaddress
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

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

    if settings.enforce_network_policy:
        from .network_policy import get_policy_engine
        hostname = urlparse(target_url).hostname
        if hostname:
            try:
                addrs = socket.getaddrinfo(hostname, None)
                engine = get_policy_engine()
                for addr in addrs:
                    ip_str = addr[4][0]
                    allowed, reason, _ = engine.check_access(
                        dest_ip=ip_str,
                        plugin_id="notification_service",
                        task_id="webhook_delivery",
                        dest_hostname=hostname,
                    )
                    if not allowed:
                        return False, f"Webhook blocked by network policy: {reason}"
            except socket.gaierror:
                return False, "Webhook URL hostname could not be resolved"

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


async def send_email_placeholder(
    target_email: str,
    payload: Dict[str, Any],
) -> tuple[bool, Optional[str]]:
    """Placeholder email channel — logs intent without sending mail yet."""
    logger.info(
        "Email notification placeholder: target=%s finding_id=%s (delivery not implemented)",
        target_email,
        payload.get("finding", {}).get("id"),
    )
    return True, None


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
        ok, error = await send_email_placeholder(target, payload)
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
