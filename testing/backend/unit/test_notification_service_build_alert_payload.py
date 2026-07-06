"""
Unit tests for build_alert_payload in notification_service.

Tests that the function correctly builds a structured alert payload
with proper field extraction, metadata parsing, and redaction.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.secuscan.notification_service import build_alert_payload


class TestBuildAlertPayload:
    def test_builds_payload_with_all_fields(self):
        """Complete finding and rule dicts produce the expected payload structure."""
        finding = {
            "id": "fid-1",
            "task_id": "tid-1",
            "plugin_id": "nmap",
            "title": "Open Port Detected",
            "category": "recon",
            "severity": "medium",
            "target": "192.168.1.1",
            "description": "Port 22 is open",
            "remediation": "Close the port",
            "metadata_json": '{"cvss": 7.5}',
        }
        rule = {
            "id": "rule-1",
            "name": "SSH Alert",
            "severity_threshold": "low",
            "channel_type": "webhook",
        }

        result = build_alert_payload(finding, rule)

        assert result["event"] == "finding.alert"
        assert result["rule"]["id"] == "rule-1"
        assert result["rule"]["name"] == "SSH Alert"
        assert result["rule"]["severity_threshold"] == "low"
        assert result["rule"]["channel_type"] == "webhook"
        assert result["finding"]["id"] == "fid-1"
        assert result["finding"]["task_id"] == "tid-1"
        assert result["finding"]["plugin_id"] == "nmap"
        assert result["finding"]["title"] == "Open Port Detected"
        assert result["finding"]["severity"] == "medium"
        assert result["finding"]["target"] == "192.168.1.1"

    def test_missing_metadata_json_produces_empty_metadata(self):
        """When finding has no metadata_json key, metadata should be empty dict."""
        finding = {"id": "fid-2", "severity": "high"}
        rule = {"id": "rule-2", "name": "Test", "severity_threshold": "medium", "channel_type": "email"}

        result = build_alert_payload(finding, rule)

        assert result["finding"]["metadata"] == {}

    def test_invalid_metadata_json_falls_back_to_raw_string(self):
        """Non-JSON metadata_json string is caught by except and stored as raw."""
        finding = {
            "id": "fid-3",
            "metadata_json": "not-valid-json",
        }
        rule = {"id": "rule-3", "name": "T", "severity_threshold": "low", "channel_type": "webhook"}

        result = build_alert_payload(finding, rule)

        assert result["finding"]["metadata"] == {"raw": "not-valid-json"}

    def test_non_string_metadata_json_raises_type_error_and_falls_back(self):
        """Non-string metadata_json (e.g. int) raises TypeError and is caught."""
        finding = {
            "id": "fid-4",
            "metadata_json": 12345,
        }
        rule = {"id": "rule-4", "name": "T", "severity_threshold": "info", "channel_type": "webhook"}

        # Should not raise — the try/except handles TypeError
        result = build_alert_payload(finding, rule)

        assert result["finding"]["metadata"] == {"raw": "12345"}

    def test_missing_finding_fields_produce_none_in_payload(self):
        """Missing optional fields in finding appear as None in the payload."""
        finding = {"id": "fid-5"}
        rule = {"id": "rule-5", "name": "Minimal", "severity_threshold": "low", "channel_type": "webhook"}

        result = build_alert_payload(finding, rule)

        assert result["finding"]["task_id"] is None
        assert result["finding"]["plugin_id"] is None
        assert result["finding"]["title"] is None
        assert result["finding"]["description"] is None
        assert result["finding"]["remediation"] is None

    def test_valid_dict_metadata_json_is_parsed_and_redacted(self):
        """Valid JSON dict in metadata_json is parsed and redacted."""
        finding = {
            "id": "fid-6",
            "metadata_json": '{"password": "secret123", "user": "admin"}',
        }
        rule = {"id": "rule-6", "name": "T", "severity_threshold": "info", "channel_type": "email"}

        result = build_alert_payload(finding, rule)

        # metadata should be parsed dict, redacted_dict applied
        assert isinstance(result["finding"]["metadata"], dict)

    def test_rule_channel_type_is_included(self):
        """rule.channel_type must be present in the payload rule section."""
        finding = {"id": "fid-7"}
        rule = {
            "id": "rule-7",
            "name": "Email Rule",
            "severity_threshold": "medium",
            "channel_type": "email",
        }

        result = build_alert_payload(finding, rule)

        assert result["rule"]["channel_type"] == "email"

    def test_redact_dict_is_called_on_result(self):
        """The returned dict must have redact_dict applied (no plain-text secrets)."""
        finding = {"id": "fid-8", "metadata_json": '{"api_key": "sk-live-12345"}'}
        rule = {"id": "rule-8", "name": "T", "severity_threshold": "low", "channel_type": "webhook"}

        with patch("backend.secuscan.notification_service.redact_dict", return_value={}) as mock_redact:
            result = build_alert_payload(finding, rule)
            mock_redact.assert_called_once()
            # The result should be the redacted version (empty dict from mock)
            assert result == {}
