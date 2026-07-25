"""
Unit tests for notification-related Pydantic models in backend/secuscan/models.py.

Covers models that are not yet tested:
- NotificationDeliveryStatus enum
- NotificationRuleCreate field validations
- HealthResponse model field defaults
- ScanWebhookSettingsRequest validation
- ErrorResponse defaults
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.secuscan.models import (
    NotificationDeliveryStatus,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationChannelType,
    NotificationSeverityThreshold,
    HealthResponse,
    ScanWebhookSettingsRequest,
    ErrorResponse,
)


# ---------------------------------------------------------------------------
# NotificationDeliveryStatus
# ---------------------------------------------------------------------------

class TestNotificationDeliveryStatus:
    def test_success_value(self):
        assert NotificationDeliveryStatus.SUCCESS.value == "success"

    def test_failed_value(self):
        assert NotificationDeliveryStatus.FAILED.value == "failed"

    def test_from_string_valid_success(self):
        assert NotificationDeliveryStatus("success") == NotificationDeliveryStatus.SUCCESS

    def test_from_string_valid_failed(self):
        assert NotificationDeliveryStatus("failed") == NotificationDeliveryStatus.FAILED

    def test_from_string_invalid_raises(self):
        with pytest.raises(ValueError):
            NotificationDeliveryStatus("unknown")

    def test_is_string_enum(self):
        assert isinstance(NotificationDeliveryStatus.SUCCESS, str)


# ---------------------------------------------------------------------------
# NotificationRuleCreate
# ---------------------------------------------------------------------------

class TestNotificationRuleCreate:
    def test_valid_rule(self):
        rule = NotificationRuleCreate(
            name="Slack alerts",
            severity_threshold=NotificationSeverityThreshold.HIGH,
            channel_type=NotificationChannelType.WEBHOOK,
            target_url_or_email="https://hooks.slack.com/services/XXX",
        )
        assert rule.name == "Slack alerts"
        assert rule.severity_threshold == NotificationSeverityThreshold.HIGH
        assert rule.is_active is True

    def test_is_active_defaults_to_true(self):
        rule = NotificationRuleCreate(
            name="Email alerts",
            severity_threshold=NotificationSeverityThreshold.MEDIUM,
            channel_type=NotificationChannelType.EMAIL,
            target_url_or_email="alerts@example.com",
        )
        assert rule.is_active is True

    def test_name_max_length_rejects_long_name(self):
        long_name = "A" * 256
        with pytest.raises(ValidationError) as exc_info:
            NotificationRuleCreate(
                name=long_name,
                severity_threshold=NotificationSeverityThreshold.INFO,
                channel_type=NotificationChannelType.WEBHOOK,
                target_url_or_email="https://example.com",
            )
        assert "name" in str(exc_info.value)

    def test_name_max_length_accepts_boundary(self):
        # Exactly 255 chars should pass
        name_255 = "A" * 255
        rule = NotificationRuleCreate(
            name=name_255,
            severity_threshold=NotificationSeverityThreshold.LOW,
            channel_type=NotificationChannelType.EMAIL,
            target_url_or_email="a@b.com",
        )
        assert len(rule.name) == 255

    def test_target_url_or_email_max_length(self):
        # Very long URL should be accepted (up to 2000)
        long_url = "https://example.com/" + "a" * 1980
        rule = NotificationRuleCreate(
            name="Long URL",
            severity_threshold=NotificationSeverityThreshold.HIGH,
            channel_type=NotificationChannelType.WEBHOOK,
            target_url_or_email=long_url,
        )
        assert len(rule.target_url_or_email) > 2000

    def test_target_url_or_email_max_length_rejected_over_2000(self):
        long_url = "https://example.com/" + "a" * 2001
        with pytest.raises(ValidationError) as exc_info:
            NotificationRuleCreate(
                name="Too long",
                severity_threshold=NotificationSeverityThreshold.HIGH,
                channel_type=NotificationChannelType.WEBHOOK,
                target_url_or_email=long_url,
            )
        assert "target_url_or_email" in str(exc_info.value)


# ---------------------------------------------------------------------------
# NotificationRuleUpdate (partial updates)
# ---------------------------------------------------------------------------

class TestNotificationRuleUpdate:
    def test_all_fields_optional(self):
        rule = NotificationRuleUpdate()
        assert rule.name is None
        assert rule.severity_threshold is None
        assert rule.channel_type is None
        assert rule.target_url_or_email is None
        assert rule.is_active is None

    def test_partial_update_name(self):
        rule = NotificationRuleUpdate(name="Updated name")
        assert rule.name == "Updated name"
        assert rule.severity_threshold is None

    def test_partial_update_is_active(self):
        rule = NotificationRuleUpdate(is_active=False)
        assert rule.is_active is False

    def test_name_max_length_enforced_in_partial_update(self):
        long_name = "B" * 256
        with pytest.raises(ValidationError):
            NotificationRuleUpdate(name=long_name)


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------

class TestHealthResponse:
    def test_required_fields(self):
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            system={},
        )
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.system == {}

    def test_optional_uptime_seconds(self):
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            system={},
            uptime_seconds=3600,
        )
        assert health.uptime_seconds == 3600

    def test_optional_limits(self):
        health = HealthResponse(
            status="healthy",
            version="1.0.0",
            system={},
            limits={"max_tasks": 100},
        )
        assert health.limits == {"max_tasks": 100}

    def test_limits_defaults_to_none(self):
        health = HealthResponse(
            status="degraded",
            version="1.0.0",
            system={"cache": "miss"},
        )
        assert health.limits is None


# ---------------------------------------------------------------------------
# ScanWebhookSettingsRequest
# ---------------------------------------------------------------------------

class TestScanWebhookSettingsRequest:
    def test_valid_url(self):
        req = ScanWebhookSettingsRequest(
            webhook_url="https://example.com/webhook"
        )
        assert req.webhook_url == "https://example.com/webhook"

    def test_url_max_length(self):
        long_url = "https://example.com/" + "a" * 1980
        req = ScanWebhookSettingsRequest(webhook_url=long_url)
        assert len(req.webhook_url) == len(long_url)

    def test_url_max_length_rejected(self):
        long_url = "https://example.com/" + "a" * 2001
        with pytest.raises(ValidationError):
            ScanWebhookSettingsRequest(webhook_url=long_url)


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------

class TestErrorResponse:
    def test_required_fields(self):
        err = ErrorResponse(error="not_found", message="Resource not found")
        assert err.error == "not_found"
        assert err.message == "Resource not found"

    def test_help_url_optional(self):
        err = ErrorResponse(error="bad_request", message="Invalid input")
        assert err.help_url is None

    def test_help_url_can_be_set(self):
        err = ErrorResponse(
            error="rate_limited",
            message="Too many requests",
            help_url="https://docs.example.com/rate-limits",
        )
        assert err.help_url == "https://docs.example.com/rate-limits"
