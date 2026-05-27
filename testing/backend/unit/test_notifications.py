"""
Unit tests for notification service.

Tests cover:
- Positive: Successful webhook delivery
- Negative: Failed delivery handling
- Negative: Redaction verification
- Deduplication logic
- Severity matching
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

import sys
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))

from backend.secuscan.notifications import (
    get_active_rules,
    severity_matches,
    is_duplicate_notification,
    redact_finding_payload,
    send_webhook_notification,
    send_email_notification,
    dispatch_notification,
    record_notification_history,
    process_notifications_for_finding,
    process_notifications,
    SEVERITY_RANKING,
    COOLDOWN_SECONDS
)
from backend.secuscan.database import init_db, get_db
from backend.secuscan.config import settings


@pytest.fixture
async def db():
    """Initialize test database."""
    await init_db(":memory:")
    db = await get_db()
    yield db
    # Cleanup is handled by the in-memory database


class TestSeverityMatching:
    """Test severity threshold matching logic."""
    
    def test_critical_matches_critical(self):
        """Critical finding should match critical threshold."""
        assert severity_matches("critical", "critical") is True
    
    def test_high_matches_critical(self):
        """High finding should NOT match critical threshold."""
        assert severity_matches("high", "critical") is False
    
    def test_critical_matches_high(self):
        """Critical finding should match high threshold."""
        assert severity_matches("critical", "high") is True
    
    def test_high_matches_high(self):
        """High finding should match high threshold."""
        assert severity_matches("high", "high") is True
    
    def test_medium_matches_high(self):
        """Medium finding should NOT match high threshold."""
        assert severity_matches("medium", "high") is False
    
    def test_case_insensitive(self):
        """Severity matching should be case-insensitive."""
        assert severity_matches("CRITICAL", "critical") is True
        assert severity_matches("High", "HIGH") is True
        assert severity_matches("LOW", "low") is True
    
    def test_unknown_severity(self):
        """Unknown severity should rank as info (0)."""
        assert severity_matches("unknown", "critical") is False
        assert severity_matches("critical", "unknown") is True


class TestRedaction:
    """Test payload redaction logic."""
    
    def test_redact_basic_finding(self):
        """Basic finding should be redacted properly."""
        finding = {
            "id": "finding:123:abc",
            "title": "SQL Injection",
            "severity": "critical",
            "category": "injection",
            "target": "example.com",
            "description": "SQL injection in login form",
            "remediation": "Use parameterized queries",
            "cvss": 9.8,
            "cve": "CVE-2024-1234"
        }
        
        redacted = redact_finding_payload(finding)
        
        # Should include safe metadata
        assert redacted["title"] == "SQL Injection"
        assert redacted["severity"] == "critical"
        assert redacted["category"] == "injection"
        assert redacted["target"] == "example.com"
        assert redacted["cvss"] == 9.8
        assert redacted["cve"] == "CVE-2024-1234"
        
        # Should NOT include raw proof or sensitive metadata
        assert "proof" not in redacted
        assert "metadata" not in redacted
    
    def test_redact_secret_in_description(self):
        """Secrets in description should be redacted."""
        finding = {
            "id": "finding:123:abc",
            "title": "Exposed API Key",
            "severity": "critical",
            "category": "secrets",
            "target": "example.com",
            "description": "Found API key: sk_live_1234567890abcdef in source code",
            "remediation": "Remove the key",
            "cvss": 9.0
        }
        
        redacted = redact_finding_payload(finding)
        
        # Secret should be redacted
        assert "sk_live_1234567890abcdef" not in redacted["description"]
        assert "[REDACTED]" in redacted["description"]
    
    def test_redact_aws_secret_key(self):
        """AWS secret keys should be redacted."""
        finding = {
            "id": "finding:123:abc",
            "title": "AWS Credentials",
            "severity": "critical",
            "category": "secrets",
            "target": "example.com",
            "description": "aws_secret_access_key = ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890/+=",
            "remediation": "Rotate credentials",
            "cvss": 9.0
        }
        
        redacted = redact_finding_payload(finding)
        
        # AWS secret should be redacted
        assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890/+=" not in redacted["description"]
        assert "[REDACTED]" in redacted["description"]
    
    def test_redact_bearer_token(self):
        """Bearer tokens should be redacted."""
        finding = {
            "id": "finding:123:abc",
            "title": "Bearer Token Leak",
            "severity": "critical",
            "category": "secrets",
            "target": "example.com",
            "description": "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "remediation": "Revoke token",
            "cvss": 9.0
        }
        
        redacted = redact_finding_payload(finding)
        
        # Bearer token should be redacted
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted["description"]
        assert "[REDACTED]" in redacted["description"]
    
    def test_redact_preserves_safe_content(self):
        """Safe content should be preserved."""
        finding = {
            "id": "finding:123:abc",
            "title": "XSS Vulnerability",
            "severity": "high",
            "category": "xss",
            "target": "example.com",
            "description": "Reflected XSS in search parameter. Input: <script>alert(1)</script>",
            "remediation": "Sanitize user input",
            "cvss": 7.5
        }
        
        redacted = redact_finding_payload(finding)
        
        # Safe technical content should be preserved
        assert "XSS" in redacted["description"]
        assert "search parameter" in redacted["description"]
        assert "Sanitize user input" in redacted["remediation"]


class TestWebhookNotification:
    """Test webhook notification delivery."""
    
    @pytest.mark.asyncio
    async def test_successful_webhook(self):
        """Test successful webhook delivery."""
        url = "https://example.com/webhook"
        payload = {"title": "Test Finding", "severity": "critical"}
        
        with patch('backend.secuscan.notifications.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            success, error = await send_webhook_notification(url, payload)
            
            assert success is True
            assert error is None
    
    @pytest.mark.asyncio
    async def test_webhook_500_error(self):
        """Test webhook returns 500 error."""
        url = "https://example.com/webhook"
        payload = {"title": "Test Finding", "severity": "critical"}
        
        with patch('backend.secuscan.notifications.httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            success, error = await send_webhook_notification(url, payload)
            
            assert success is False
            assert error is not None
            assert "500" in error
    
    @pytest.mark.asyncio
    async def test_webhook_timeout(self):
        """Test webhook timeout."""
        url = "https://example.com/webhook"
        payload = {"title": "Test Finding", "severity": "critical"}
        
        with patch('backend.secuscan.notifications.httpx.AsyncClient') as mock_client:
            from httpx import TimeoutException
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=TimeoutException("Request timed out")
            )
            
            success, error = await send_webhook_notification(url, payload)
            
            assert success is False
            assert error is not None
            assert "timed out" in error.lower()
    
    @pytest.mark.asyncio
    async def test_webhook_network_error(self):
        """Test webhook network error."""
        url = "https://example.com/webhook"
        payload = {"title": "Test Finding", "severity": "critical"}
        
        with patch('backend.secuscan.notifications.httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=Exception("Connection refused")
            )
            
            success, error = await send_webhook_notification(url, payload)
            
            assert success is False
            assert error is not None
            assert "failed" in error.lower()


class TestEmailNotification:
    """Test email notification delivery."""
    
    @pytest.mark.asyncio
    async def test_email_placeholder(self):
        """Test email notification (placeholder implementation)."""
        email = "test@example.com"
        payload = {"title": "Test Finding", "severity": "critical"}
        
        success, error = await send_email_notification(email, payload)
        
        # Placeholder returns True but logs warning
        assert success is True
        assert error is None


class TestDeduplication:
    """Test notification deduplication logic."""
    
    @pytest.mark.asyncio
    async def test_no_duplicate_first_notification(self, db):
        """First notification should not be considered duplicate."""
        rule_id = "rule-123"
        finding_id = "finding-456"
        
        is_dup = await is_duplicate_notification(rule_id, finding_id)
        
        assert is_dup is False
    
    @pytest.mark.asyncio
    async def test_duplicate_within_cooldown(self, db):
        """Notification within cooldown window should be duplicate."""
        rule_id = "rule-123"
        finding_id = "finding-456"
        
        # Record first notification
        await record_notification_history(rule_id, finding_id, "success")
        
        # Check for duplicate immediately
        is_dup = await is_duplicate_notification(rule_id, finding_id)
        
        assert is_dup is True
    
    @pytest.mark.asyncio
    async def test_no_duplicate_after_cooldown(self, db):
        """Notification after cooldown window should not be duplicate."""
        rule_id = "rule-123"
        finding_id = "finding-456"
        
        # Record notification with old timestamp
        await db.execute(
            """
            INSERT INTO notification_history (id, rule_id, finding_id, status, sent_at)
            VALUES (?, ?, ?, ?, datetime('now', '-2 hours'))
            """,
            ("history-123", rule_id, finding_id, "success")
        )
        
        # Check for duplicate after cooldown
        is_dup = await is_duplicate_notification(rule_id, finding_id)
        
        assert is_dup is False


class TestDispatchNotification:
    """Test notification dispatch logic."""
    
    @pytest.mark.asyncio
    async def test_dispatch_webhook(self, db):
        """Test dispatching webhook notification."""
        rule = {
            "id": "rule-123",
            "name": "Test Rule",
            "channel_type": "webhook",
            "target_url_or_email": "https://example.com/webhook"
        }
        finding = {
            "id": "finding-456",
            "title": "Test Finding",
            "severity": "critical",
            "category": "injection",
            "target": "example.com",
            "description": "Test description",
            "remediation": "Test remediation"
        }
        
        with patch('backend.secuscan.notifications.send_webhook_notification') as mock_webhook:
            mock_webhook.return_value = (True, None)
            
            success, error = await dispatch_notification(rule, finding)
            
            assert success is True
            assert error is None
            mock_webhook.assert_called_once()
            
            # Verify payload was redacted
            call_args = mock_webhook.call_args[0]
            payload = call_args[1]
            assert payload["title"] == "Test Finding"
            assert payload["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_dispatch_email(self, db):
        """Test dispatching email notification."""
        rule = {
            "id": "rule-123",
            "name": "Test Rule",
            "channel_type": "email",
            "target_url_or_email": "test@example.com"
        }
        finding = {
            "id": "finding-456",
            "title": "Test Finding",
            "severity": "critical",
            "category": "injection",
            "target": "example.com",
            "description": "Test description",
            "remediation": "Test remediation"
        }
        
        with patch('backend.secuscan.notifications.send_email_notification') as mock_email:
            mock_email.return_value = (True, None)
            
            success, error = await dispatch_notification(rule, finding)
            
            assert success is True
            assert error is None
            mock_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_unknown_channel(self, db):
        """Test dispatching with unknown channel type."""
        rule = {
            "id": "rule-123",
            "name": "Test Rule",
            "channel_type": "unknown",
            "target_url_or_email": "test@example.com"
        }
        finding = {
            "id": "finding-456",
            "title": "Test Finding",
            "severity": "critical",
            "category": "injection",
            "target": "example.com",
            "description": "Test description",
            "remediation": "Test remediation"
        }
        
        success, error = await dispatch_notification(rule, finding)
        
        assert success is False
        assert error is not None
        assert "Unknown channel type" in error


class TestProcessNotifications:
    """Test end-to-end notification processing."""
    
    @pytest.mark.asyncio
    async def test_process_critical_finding(self, db):
        """Test processing a critical finding."""
        # Create an active rule
        await db.execute(
            """
            INSERT INTO notification_rules (id, name, severity_threshold, channel_type, target_url_or_email, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            ("rule-123", "Critical Rule", "high", "webhook", "https://example.com/webhook", 1)
        )
        
        finding = {
            "id": "finding-456",
            "title": "Critical Finding",
            "severity": "critical",
            "category": "injection",
            "target": "example.com",
            "description": "Critical vulnerability",
            "remediation": "Fix immediately"
        }
        
        with patch('backend.secuscan.notifications.dispatch_notification') as mock_dispatch:
            mock_dispatch.return_value = (True, None)
            
            await process_notifications_for_finding(finding)
            
            # Should have dispatched notification
            mock_dispatch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_low_severity_finding(self, db):
        """Test that low-severity findings are not processed."""
        # Create an active rule
        await db.execute(
            """
            INSERT INTO notification_rules (id, name, severity_threshold, channel_type, target_url_or_email, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            ("rule-123", "High Rule", "high", "webhook", "https://example.com/webhook", 1)
        )
        
        finding = {
            "id": "finding-456",
            "title": "Low Finding",
            "severity": "low",
            "category": "info",
            "target": "example.com",
            "description": "Low severity issue",
            "remediation": "Optional fix"
        }
        
        with patch('backend.secuscan.notifications.dispatch_notification') as mock_dispatch:
            await process_notifications_for_finding(finding)
            
            # Should NOT have dispatched notification
            mock_dispatch.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_multiple_findings(self, db):
        """Test processing multiple findings."""
        # Create an active rule
        await db.execute(
            """
            INSERT INTO notification_rules (id, name, severity_threshold, channel_type, target_url_or_email, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
            ("rule-123", "High Rule", "high", "webhook", "https://example.com/webhook", 1)
        )
        
        findings = [
            {
                "id": "finding-1",
                "title": "Critical Finding",
                "severity": "critical",
                "category": "injection",
                "target": "example.com",
                "description": "Critical vulnerability",
                "remediation": "Fix immediately"
            },
            {
                "id": "finding-2",
                "title": "High Finding",
                "severity": "high",
                "category": "xss",
                "target": "example.com",
                "description": "High severity issue",
                "remediation": "Fix soon"
            },
            {
                "id": "finding-3",
                "title": "Low Finding",
                "severity": "low",
                "category": "info",
                "target": "example.com",
                "description": "Low severity issue",
                "remediation": "Optional fix"
            }
        ]
        
        with patch('backend.secuscan.notifications.dispatch_notification') as mock_dispatch:
            mock_dispatch.return_value = (True, None)
            
            await process_notifications(findings)
            
            # Should have dispatched for critical and high only
            assert mock_dispatch.call_count == 2


class TestNotificationHistory:
    """Test notification history recording."""
    
    @pytest.mark.asyncio
    async def test_record_success_history(self, db):
        """Test recording successful notification."""
        rule_id = "rule-123"
        finding_id = "finding-456"
        
        await record_notification_history(rule_id, finding_id, "success")
        
        history = await db.fetchone(
            "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
            (rule_id, finding_id)
        )
        
        assert history is not None
        assert history["status"] == "success"
        assert history["error_message"] is None
    
    @pytest.mark.asyncio
    async def test_record_failure_history(self, db):
        """Test recording failed notification."""
        rule_id = "rule-123"
        finding_id = "finding-456"
        error_msg = "Webhook timeout"
        
        await record_notification_history(rule_id, finding_id, "failed", error_msg)
        
        history = await db.fetchone(
            "SELECT * FROM notification_history WHERE rule_id = ? AND finding_id = ?",
            (rule_id, finding_id)
        )
        
        assert history is not None
        assert history["status"] == "failed"
        assert history["error_message"] == error_msg
