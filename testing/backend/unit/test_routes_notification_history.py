"""
Unit tests for _serialize_notification_history helper.

Imports the real production function from backend.secuscan.routes_json_helpers
so a regression in the actual implementation is caught by these tests.
"""

from backend.secuscan.routes_json_helpers import _serialize_notification_history


class TestSerializeNotificationHistory:
    def test_full_row_all_fields(self):
        row = {
            "id": "hist-1",
            "rule_id": "rule-42",
            "finding_id": "finding-99",
            "status": "sent",
            "error_message": None,
            "sent_at": "2026-06-01T12:00:00Z",
        }
        result = _serialize_notification_history(row)
        assert result["id"] == "hist-1"
        assert result["rule_id"] == "rule-42"
        assert result["finding_id"] == "finding-99"
        assert result["status"] == "sent"
        assert result["error_message"] is None
        assert result["sent_at"] == "2026-06-01T12:00:00Z"

    def test_with_error_message_populated(self):
        row = {
            "id": "hist-2",
            "rule_id": "rule-1",
            "finding_id": "finding-5",
            "status": "failed",
            "error_message": "Connection refused",
            "sent_at": "2026-06-01T14:00:00Z",
        }
        result = _serialize_notification_history(row)
        assert result["error_message"] == "Connection refused"

    def test_missing_optional_error_message(self):
        row = {
            "id": "hist-3",
            "rule_id": "rule-1",
            "finding_id": "finding-5",
            "status": "sent",
        }
        result = _serialize_notification_history(row)
        assert result["error_message"] is None
        assert result["sent_at"] is None

    def test_missing_optional_sent_at(self):
        row = {
            "id": "hist-4",
            "rule_id": "rule-2",
            "finding_id": "finding-10",
            "status": "pending",
        }
        result = _serialize_notification_history(row)
        assert result["sent_at"] is None

    def test_extra_keys_not_preserved(self):
        """Only the documented fields are included; extra keys are filtered out."""
        row = {
            "id": "hist-5",
            "rule_id": "rule-3",
            "finding_id": "finding-20",
            "status": "sent",
            "extra_meta": {"retry_count": 2},
        }
        result = _serialize_notification_history(row)
        assert "extra_meta" not in result

    def test_all_required_keys_present(self):
        row = {
            "id": "hist-6",
            "rule_id": "rule-4",
            "finding_id": "finding-30",
            "status": "failed",
        }
        result = _serialize_notification_history(row)
        required_keys = {"id", "rule_id", "finding_id", "status"}
        assert required_keys.issubset(result.keys())
