"""
Unit tests for serialize_notification_rule in
backend.secuscan.routes_notification_helpers.
"""

import pytest
from backend.secuscan.routes_notification_helpers import serialize_notification_rule


class TestSerializeNotificationRule:
    def test_all_fields_present(self):
        row = {
            "id": 42,
            "name": "Discord Alert",
            "severity_threshold": 7,
            "channel_type": "webhook",
            "target_url_or_email": "https://discord.com/api/webhooks/1/abc",
            "is_active": 1,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
        }
        result = serialize_notification_rule(row)
        assert result["id"] == 42
        assert result["name"] == "Discord Alert"
        assert result["severity_threshold"] == 7
        assert result["channel_type"] == "webhook"
        assert result["target_url_or_email"] == "https://discord.com/api/webhooks/1/abc"
        assert result["is_active"] is True
        assert result["created_at"] == "2026-01-01T00:00:00Z"
        assert result["updated_at"] == "2026-01-02T00:00:00Z"

    def test_is_active_true_coerced_from_truthy_value(self):
        for val in [1, True, "yes", "1"]:
            row = {"id": 1, "name": "R", "severity_threshold": 5,
                   "channel_type": "email", "target_url_or_email": "a@b.com",
                   "is_active": val}
            result = serialize_notification_rule(row)
            assert result["is_active"] is True, f"is_active={val!r}"

    def test_is_active_false_coerced_from_falsy_value(self):
        for val in [0, False, None, ""]:
            row = {"id": 1, "name": "R", "severity_threshold": 5,
                   "channel_type": "email", "target_url_or_email": "a@b.com",
                   "is_active": val}
            result = serialize_notification_rule(row)
            assert result["is_active"] is False, f"is_active={val!r}"

    def test_missing_created_at_yields_none(self):
        row = {"id": 1, "name": "R", "severity_threshold": 5,
               "channel_type": "email", "target_url_or_email": "a@b.com",
               "is_active": True}
        result = serialize_notification_rule(row)
        assert result["created_at"] is None

    def test_missing_updated_at_yields_none(self):
        row = {"id": 1, "name": "R", "severity_threshold": 5,
               "channel_type": "email", "target_url_or_email": "a@b.com",
               "is_active": True}
        result = serialize_notification_rule(row)
        assert result["updated_at"] is None

    def test_email_channel_preserved(self):
        row = {"id": 3, "name": "Email Report", "severity_threshold": 3,
               "channel_type": "email", "target_url_or_email": "ops@corp.com",
               "is_active": 1}
        result = serialize_notification_rule(row)
        assert result["channel_type"] == "email"

    def test_severity_threshold_unchanged(self):
        row = {"id": 4, "name": "T", "severity_threshold": 0,
               "channel_type": "webhook", "target_url_or_email": "https://x.com",
               "is_active": False}
        result = serialize_notification_rule(row)
        assert result["severity_threshold"] == 0
