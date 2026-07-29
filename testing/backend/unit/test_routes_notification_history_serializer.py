"""
Unit tests for backend.secuscan.routes_notification_helpers._serialize_notification_history.

Run with:
    python3 -m pytest testing/backend/unit/test_routes_notification_history_serializer.py -v --noconftest
"""

from __future__ import annotations

import pytest

from backend.secuscan.routes_notification_helpers import _serialize_notification_history


class TestSerializeNotificationHistory:
    def test_complete_row_returns_correct_shape(self):
        row = {
            "id": "hist-123",
            "rule_id": "rule-456",
            "finding_id": "find-789",
            "status": "sent",
            "error_message": None,
            "sent_at": "2026-07-29T10:00:00Z",
        }
        result = _serialize_notification_history(row)
        assert result == {
            "id": "hist-123",
            "rule_id": "rule-456",
            "finding_id": "find-789",
            "status": "sent",
            "error_message": None,
            "sent_at": "2026-07-29T10:00:00Z",
        }

    def test_missing_error_message_uses_none(self):
        row = {
            "id": "hist-1",
            "rule_id": "rule-1",
            "finding_id": "find-1",
            "status": "failed",
            "sent_at": None,
        }
        result = _serialize_notification_history(row)
        assert result["error_message"] is None
        assert result["sent_at"] is None

    def test_is_active_not_present(self):
        # The function should only return the fields it explicitly defines
        row = {
            "id": "hist-2",
            "rule_id": "rule-2",
            "finding_id": "find-2",
            "status": "pending",
            "error_message": "timeout",
            "sent_at": "2026-07-28T12:00:00Z",
        }
        result = _serialize_notification_history(row)
        # is_active should NOT be in the output (unlike notification rule serializer)
        assert "is_active" not in result

    def test_required_fields_always_present(self):
        row = {
            "id": "hist-min",
            "rule_id": "rule-min",
            "finding_id": "find-min",
            "status": "skipped",
            "error_message": None,
            "sent_at": None,
        }
        result = _serialize_notification_history(row)
        assert "id" in result
        assert "rule_id" in result
        assert "finding_id" in result
        assert "status" in result
        assert "error_message" in result
        assert "sent_at" in result

    def test_status_value_preserved(self):
        for status in ("pending", "sent", "failed", "skipped"):
            row = {
                "id": "h", "rule_id": "r", "finding_id": "f",
                "status": status, "error_message": None, "sent_at": None,
            }
            result = _serialize_notification_history(row)
            assert result["status"] == status
