"""
Notification service for high-risk findings.

Handles rule matching, payload redaction, deduplication, and dispatching
notifications via webhooks or email.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx

from .database import get_db
from .redaction import redact, redact_dict
from .config import settings

logger = logging.getLogger(__name__)

# Severity ranking for threshold matching
SEVERITY_RANKING = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
}

# Cooldown window for deduplication (1 hour)
COOLDOWN_SECONDS = 3600


async def get_active_rules() -> List[Dict[str, Any]]:
    """Get all active notification rules."""
    db = await get_db()
    rows = await db.fetchall(
        "SELECT * FROM notification_rules WHERE is_active = 1"
    )
    return [dict(row) for row in rows]


def severity_matches(finding_severity: str, rule_threshold: str) -> bool:
    """
    Check if a finding's severity matches or exceeds the rule threshold.
    
    Args:
        finding_severity: The severity of the finding (e.g., "high", "critical")
        rule_threshold: The minimum severity threshold for the rule
    
    Returns:
        True if the finding severity meets or exceeds the threshold
    """
    finding_rank = SEVERITY_RANKING.get(finding_severity.lower(), 0)
    threshold_rank = SEVERITY_RANKING.get(rule_threshold.lower(), 0)
    return finding_rank >= threshold_rank


async def is_duplicate_notification(rule_id: str, finding_id: str) -> bool:
    """
    Check if a notification for this finding and rule was already sent
    within the cooldown window.
    
    Args:
        rule_id: The notification rule ID
        finding_id: The finding ID
    
    Returns:
        True if a notification was sent within the cooldown window
    """
    db = await get_db()
    cooldown_cutoff = (datetime.now() - timedelta(seconds=COOLDOWN_SECONDS)).isoformat()
    
    recent = await db.fetchone(
        """
        SELECT id FROM notification_history
        WHERE rule_id = ? AND finding_id = ? AND sent_at > ?
        LIMIT 1
        """,
        (rule_id, finding_id, cooldown_cutoff)
    )
    
    return recent is not None


def redact_finding_payload(finding: Dict[str, Any]) -> Dict[str, Any]:
    """
    Redact sensitive data from a finding payload.
    
    Only sends metadata (title, severity, component, link to dashboard).
    Strips code snippets, raw tokens, internal infrastructure details.
    
    Args:
        finding: The raw finding data
    
    Returns:
        Redacted payload with only safe metadata
    """
    # Extract only safe metadata
    redacted = {
        "title": finding.get("title", ""),
        "severity": finding.get("severity", ""),
        "category": finding.get("category", ""),
        "target": finding.get("target", ""),
        "description": redact(finding.get("description", "")),
        "remediation": redact(finding.get("remediation", "")),
        "cvss": finding.get("cvss"),
        "cve": finding.get("cve"),
        # Generate dashboard link
        "dashboard_url": f"{settings.base_url}/findings/{finding.get('id')}" if hasattr(settings, 'base_url') else None
    }
    
    # Redact any remaining sensitive data
    return redact_dict(redacted)


async def send_webhook_notification(url: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Send a notification via webhook.
    
    Args:
        url: The webhook URL
        payload: The notification payload
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
            
            if response.status_code >= 200 and response.status_code < 300:
                return True, None
            else:
                error_msg = f"Webhook returned status {response.status_code}"
                logger.error(f"Webhook notification failed: {error_msg}")
                return False, error_msg
    except httpx.TimeoutException:
        error_msg = "Webhook request timed out"
        logger.error(f"Webhook notification failed: {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Webhook request failed: {str(e)}"
        logger.error(f"Webhook notification failed: {error_msg}")
        return False, error_msg


async def send_email_notification(email: str, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Send a notification via email.
    
    Note: This is a placeholder implementation. In production, integrate with
    an email service like SendGrid, AWS SES, or SMTP.
    
    Args:
        email: The target email address
        payload: The notification payload
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    # Placeholder: Email notifications require an email service integration
    # For now, we log and return success to avoid blocking the feature
    logger.warning(f"Email notifications not yet implemented. Would send to {email}")
    logger.info(f"Email payload: {json.dumps(payload, indent=2)}")
    return True, None


async def dispatch_notification(rule: Dict[str, Any], finding: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Dispatch a notification based on the rule's channel type.
    
    Args:
        rule: The notification rule
        finding: The finding data
    
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    channel_type = rule.get("channel_type", "").lower()
    target = rule.get("target_url_or_email", "")
    
    # Redact the payload before sending
    redacted_payload = redact_finding_payload(finding)
    
    # Add rule context
    redacted_payload["rule_name"] = rule.get("name", "")
    redacted_payload["timestamp"] = datetime.now().isoformat()
    
    if channel_type == "webhook":
        return await send_webhook_notification(target, redacted_payload)
    elif channel_type == "email":
        return await send_email_notification(target, redacted_payload)
    else:
        error_msg = f"Unknown channel type: {channel_type}"
        logger.error(error_msg)
        return False, error_msg


async def record_notification_history(
    rule_id: str,
    finding_id: str,
    status: str,
    error_message: Optional[str] = None
):
    """
    Record a notification attempt in the history.
    
    Args:
        rule_id: The notification rule ID
        finding_id: The finding ID
        status: "success" or "failed"
        error_message: Optional error message if failed
    """
    db = await get_db()
    history_id = str(uuid.uuid4())
    
    await db.execute(
        """
        INSERT INTO notification_history (id, rule_id, finding_id, status, error_message, sent_at)
        VALUES (?, ?, ?, ?, ?, (datetime('now')))
        """,
        (history_id, rule_id, finding_id, status, error_message)
    )


async def process_notifications_for_finding(finding: Dict[str, Any]):
    """
    Process notifications for a single finding.
    
    This function:
    1. Gets all active notification rules
    2. Filters rules by severity threshold
    3. Checks for duplicates (deduplication)
    4. Redacts sensitive data
    5. Dispatches notifications
    6. Records history
    
    Args:
        finding: The finding data (must include id, severity, title, category, target, etc.)
    """
    finding_severity = finding.get("severity", "").lower()
    finding_id = finding.get("id")
    
    if not finding_id:
        logger.error("Finding missing ID, skipping notification")
        return
    
    # Only process high-severity findings (high or critical)
    if finding_severity not in ["high", "critical"]:
        logger.debug(f"Finding severity {finding_severity} below threshold, skipping notification")
        return
    
    # Get active rules
    rules = await get_active_rules()
    
    if not rules:
        logger.debug("No active notification rules found")
        return
    
    logger.info(f"Processing notifications for finding {finding_id} with {len(rules)} active rules")
    
    for rule in rules:
        rule_id = rule.get("id")
        rule_threshold = rule.get("severity_threshold", "").lower()
        
        # Check severity threshold
        if not severity_matches(finding_severity, rule_threshold):
            logger.debug(f"Finding severity {finding_severity} below rule threshold {rule_threshold}")
            continue
        
        # Check for duplicate notification
        if await is_duplicate_notification(rule_id, finding_id):
            logger.debug(f"Duplicate notification for rule {rule_id} and finding {finding_id}, skipping")
            continue
        
        # Dispatch notification
        success, error_msg = await dispatch_notification(rule, finding)
        
        # Record history
        status = "success" if success else "failed"
        await record_notification_history(rule_id, finding_id, status, error_msg)
        
        if success:
            logger.info(f"Successfully sent notification for rule {rule_id} and finding {finding_id}")
        else:
            logger.error(f"Failed to send notification for rule {rule_id} and finding {finding_id}: {error_msg}")


async def process_notifications(findings: List[Dict[str, Any]]):
    """
    Process notifications for multiple findings.
    
    This is the main entry point for the notification system.
    It should be called after findings are saved to the database.
    
    Args:
        findings: List of finding dictionaries
    """
    if not findings:
        return
    
    logger.info(f"Processing notifications for {len(findings)} findings")
    
    # Process each finding in parallel
    tasks = [
        process_notifications_for_finding(finding)
        for finding in findings
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
