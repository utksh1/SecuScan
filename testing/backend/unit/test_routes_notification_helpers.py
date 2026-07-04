"""
Unit tests for _serialize_notification_rule helper.

Imports the real production function from backend.secuscan.routes_json_helpers
so a regression in the actual implementation is caught by these tests.
"""

from backend.secuscan.routes_json_helpers import _serialize_notification_rule


class TestSerializeNotificationRule:
    def test_full_row_all_fields(self):
        row = {
            "id": "rule-1",
            "name": "Critical Alerts",
            "severity_threshold": "critical",
            "channel_type": "webhook",
            "target_url_or_email": "https://example.com/webhook",
            "is_active": True,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        result = _serialize_notification_rule(row)
        assert result["id"] == "rule-1"
        assert result["name"] == "Critical Alerts"
        assert result["severity_threshold"] == "critical"
        assert result["channel_type"] == "webhook"
        assert result["target_url_or_email"] == "https://example.com/webhook"
        assert result["is_active"] is True
        assert result["created_at"] == "2026-01-01T00:00:00Z"
        assert result["updated_at"] == "2026-01-02T00:00:00Z"

    def test_missing_optional_is_active_treated_as_false(self):
        row = {
            "id": "rule-2",
            "name": "Email Alerts",
            "severity_threshold": "high",
            "channel_type": "email",
            "target_url_or_email": "admin@example.com",
        }
        result = _serialize_notification_rule(row)
        assert result["is_active"] is False

    def test_is_active_int_zero_is_false(self):
        row = {
            "id": "rule-3",
            "name": "Test Rule",
            "severity_threshold": "medium",
            "channel_type": "email",
            "target_url_or_email": "test@example.com",
            "is_active": 0,
        }
        result = _serialize_notification_rule(row)
        assert result["is_active"] is False

    def test_is_active_int_one_is_true(self):
        row = {
            "id": "rule-4",
            "name": "Active Rule",
            "severity_threshold": "high",
            "channel_type": "webhook",
            "target_url_or_email": "https://example.com/hook",
            "is_active": 1,
        }
        result = _serialize_notification_rule(row)
        assert result["is_active"] is True

    def test_missing_optional_created_at_is_none(self):
        row = {
            "id": "rule-5",
            "name": "Rule Without Timestamps",
            "severity_threshold": "low",
            "channel_type": "email",
            "target_url_or_email": "noreply@example.com",
        }
        result = _serialize_notification_rule(row)
        assert result["created_at"] is None
        assert result["updated_at"] is None

    def test_extra_keys_not_preserved(self):
        """Only the documented fields are included; extra keys are filtered out."""
        row = {
            "id": "rule-6",
            "name": "Rule With Extra",
            "severity_threshold": "critical",
            "channel_type": "webhook",
            "target_url_or_email": "https://example.com/extra",
            "extra_field": "not-present",
        }
        result = _serialize_notification_rule(row)
        assert "extra_field" not in result

    def test_all_required_fields_present(self):
        row = {
            "id": "rule-7",
            "name": "Minimal Rule",
            "severity_threshold": "info",
            "channel_type": "email",
            "target_url_or_email": "info@example.com",
        }
        result = _serialize_notification_rule(row)
        required_keys = {"id", "name", "severity_threshold", "channel_type",
                         "target_url_or_email", "is_active"}
        assert required_keys.issubset(result.keys())
