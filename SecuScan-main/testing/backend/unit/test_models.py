"""
Unit tests for Pydantic models in backend/secuscan/models.py.

Extends the basic tests in this file with field validation edge cases.

Covers:
- Finding: optional fields, default values, field constraints
- TaskCreateRequest: required fields, validation
- TaskResponse: optional datetime fields, None handling
- PluginField: type field, required flag, options
- ExecutionContext: defaults for validation_mode and evidence_level
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from backend.secuscan.models import (
    Finding,
    TaskCreateRequest,
    TaskResponse,
    PluginField,
    ExecutionContext,
    PluginFieldType,
    TaskStatus,
    ValidationMode,
    EvidenceLevel,
    FindingKind,
    AnalystStatus,
    RetestStatus,
    NotificationChannelType,
    NotificationSeverityThreshold,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    ErrorResponse,
    HealthResponse,
    SafetyLevel,
    PluginListResponse,
)


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------

class TestFindingDefaults:
    def test_validated_defaults_to_false(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.validated is False

    def test_occurrence_count_defaults_to_one(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.occurrence_count == 1

    def test_analyst_status_defaults_to_new(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.analyst_status == AnalystStatus.NEW

    def test_retest_status_defaults_to_not_requested(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.retest_status == RetestStatus.NOT_REQUESTED

    def test_finding_kind_defaults_to_observation(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.finding_kind == FindingKind.OBSERVATION

    def test_evidence_defaults_to_empty_list(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.evidence == []
        # ensure it is a real list, not None
        assert isinstance(finding.evidence, list)

    def test_asset_refs_defaults_to_empty_list(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
        )
        assert finding.asset_refs == []
        assert isinstance(finding.asset_refs, list)

    def test_optional_fields_accept_none(self):
        finding = Finding(
            title="Test",
            category="test",
            severity="medium",
            target="https://example.com",
            description="desc",
            cvss=None,
            cve=None,
            proof=None,
        )
        assert finding.cvss is None
        assert finding.cve is None
        assert finding.proof is None


# ---------------------------------------------------------------------------
# TaskCreateRequest
# ---------------------------------------------------------------------------

class TestTaskCreateRequest:
    def test_required_plugin_id(self):
        # Missing plugin_id should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateRequest(inputs={})
        assert "plugin_id" in str(exc_info.value)

    def test_required_inputs(self):
        # Missing inputs should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            TaskCreateRequest(plugin_id="nuclei")
        assert "inputs" in str(exc_info.value)

    def test_consent_granted_defaults_to_false(self):
        req = TaskCreateRequest(plugin_id="nuclei", inputs={})
        assert req.consent_granted is False

    def test_execution_context_has_defaults(self):
        req = TaskCreateRequest(plugin_id="nuclei", inputs={})
        assert req.execution_context.validation_mode == ValidationMode.PROOF
        assert req.execution_context.evidence_level == EvidenceLevel.STANDARD


# ---------------------------------------------------------------------------
# TaskResponse
# ---------------------------------------------------------------------------

class TestTaskResponse:
    def test_optional_started_at_accepts_none(self):
        resp = TaskResponse(
            task_id="t1",
            plugin_id="nuclei",
            tool="nuclei",
            target="https://example.com",
            status=TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            started_at=None,
        )
        assert resp.started_at is None

    def test_optional_completed_at_accepts_none(self):
        resp = TaskResponse(
            task_id="t1",
            plugin_id="nuclei",
            tool="nuclei",
            target="https://example.com",
            status=TaskStatus.RUNNING,
            created_at=datetime.now(timezone.utc),
            completed_at=None,
        )
        assert resp.completed_at is None

    def test_optional_duration_accepts_none(self):
        resp = TaskResponse(
            task_id="t1",
            plugin_id="nuclei",
            tool="nuclei",
            target="https://example.com",
            status=TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc),
            duration_seconds=None,
        )
        assert resp.duration_seconds is None


# ---------------------------------------------------------------------------
# PluginField
# ---------------------------------------------------------------------------

class TestPluginField:
    def test_required_fields(self):
        # Missing id raises
        with pytest.raises(ValidationError) as exc_info:
            PluginField(label="Name", type=PluginFieldType.STRING)
        assert "id" in str(exc_info.value)

    def test_required_label(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginField(id="name", type=PluginFieldType.STRING)
        assert "label" in str(exc_info.value)

    def test_required_type(self):
        with pytest.raises(ValidationError) as exc_info:
            PluginField(id="name", label="Name")
        assert "type" in str(exc_info.value)

    def test_required_defaults_to_false(self):
        field = PluginField(id="name", label="Name", type=PluginFieldType.STRING)
        assert field.required is False

    def test_options_can_be_none(self):
        field = PluginField(id="name", label="Name", type=PluginFieldType.SELECT, options=None)
        assert field.options is None

    def test_placeholder_can_be_none(self):
        field = PluginField(id="name", label="Name", type=PluginFieldType.STRING, placeholder=None)
        assert field.placeholder is None

    def test_all_field_types_accepted(self):
        for ft in PluginFieldType:
            field = PluginField(id="test", label="Test", type=ft)
            assert field.type == ft


# ---------------------------------------------------------------------------
# ExecutionContext
# ---------------------------------------------------------------------------

class TestExecutionContext:
    def test_validation_mode_defaults_to_proof(self):
        ctx = ExecutionContext()
        assert ctx.validation_mode == ValidationMode.PROOF

    def test_evidence_level_defaults_to_standard(self):
        ctx = ExecutionContext()
        assert ctx.evidence_level == EvidenceLevel.STANDARD

    def test_scan_profile_defaults_to_standard(self):
        ctx = ExecutionContext()
        assert ctx.scan_profile == "standard"

    def test_optional_fields_accept_none(self):
        ctx = ExecutionContext(
            target_policy_id=None,
            credential_profile_id=None,
            session_profile_id=None,
        )
        assert ctx.target_policy_id is None
        assert ctx.credential_profile_id is None
        assert ctx.session_profile_id is None


# ---------------------------------------------------------------------------
# NotificationChannelType enum
# ---------------------------------------------------------------------------

def test_notification_channel_type_valid_values():
    assert NotificationChannelType.WEBHOOK.value == "webhook"
    assert NotificationChannelType.EMAIL.value == "email"


def test_notification_channel_type_from_string():
    assert NotificationChannelType("webhook") == NotificationChannelType.WEBHOOK
    assert NotificationChannelType("email") == NotificationChannelType.EMAIL


def test_notification_channel_type_invalid_raises():
    with pytest.raises(ValueError):
        NotificationChannelType("sms")


# ---------------------------------------------------------------------------
# NotificationSeverityThreshold enum
# ---------------------------------------------------------------------------

def test_notification_severity_threshold_valid_values():
    for name in ["critical", "high", "medium", "low", "info"]:
        assert NotificationSeverityThreshold(name).value == name


def test_notification_severity_threshold_invalid_raises():
    with pytest.raises(ValueError):
        NotificationSeverityThreshold("urgent")


# ---------------------------------------------------------------------------
# NotificationRuleCreate
# ---------------------------------------------------------------------------

def test_notification_rule_create_valid():
    rule = NotificationRuleCreate(
        name="my-hook",
        severity_threshold=NotificationSeverityThreshold.HIGH,
        channel_type=NotificationChannelType.WEBHOOK,
        target_url_or_email="https://example.com/hook",
    )
    assert rule.name == "my-hook"
    assert rule.severity_threshold == NotificationSeverityThreshold.HIGH
    assert rule.is_active is True


def test_notification_rule_create_invalid_channel_type():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="bad-hook",
            severity_threshold=NotificationSeverityThreshold.HIGH,
            channel_type="sms",
            target_url_or_email="https://example.com/hook",
        )


def test_notification_rule_create_invalid_severity():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="bad-hook",
            severity_threshold="not_a_severity",
            channel_type=NotificationChannelType.WEBHOOK,
            target_url_or_email="https://example.com/hook",
        )


def test_notification_rule_create_missing_name():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            severity_threshold=NotificationSeverityThreshold.HIGH,
            channel_type=NotificationChannelType.EMAIL,
            target_url_or_email="test@example.com",
        )


# ---------------------------------------------------------------------------
# NotificationRuleUpdate
# ---------------------------------------------------------------------------

def test_notification_rule_update_all_optional():
    rule = NotificationRuleUpdate()
    assert rule.name is None
    assert rule.severity_threshold is None
    assert rule.channel_type is None


def test_notification_rule_update_partial():
    rule = NotificationRuleUpdate(name="updated-hook")
    assert rule.name == "updated-hook"
    assert rule.severity_threshold is None


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------

def test_error_response_required_fields():
    err = ErrorResponse(error="not_found", message="Resource not found")
    assert err.error == "not_found"
    assert err.message == "Resource not found"
    assert err.field is None
    assert err.details is None


def test_error_response_with_optional_fields():
    err = ErrorResponse(
        error="validation_error",
        message="Invalid input",
        field="target",
        details={"reason": "invalid_url"},
    )
    assert err.field == "target"
    assert err.details["reason"] == "invalid_url"


# ---------------------------------------------------------------------------
# HealthResponse
# ---------------------------------------------------------------------------

def test_health_response_required_fields():
    health = HealthResponse(
        status="healthy",
        version="1.0.0",
        system={"cpu": "ok"},
    )
    assert health.status == "healthy"
    assert health.version == "1.0.0"
    assert health.uptime_seconds is None
    assert health.limits is None


def test_health_response_all_fields():
    health = HealthResponse(
        status="degraded",
        version="1.0.0",
        uptime_seconds=3600,
        system={"cpu": "high"},
        limits={"max_tasks": 100},
    )
    assert health.uptime_seconds == 3600
    assert health.limits["max_tasks"] == 100


# ---------------------------------------------------------------------------
# SafetyLevel enum
# ---------------------------------------------------------------------------

def test_safety_level_valid_values():
    for name in ["safe", "intrusive", "exploit"]:
        assert SafetyLevel(name).value == name


def test_safety_level_invalid_raises():
    with pytest.raises(ValueError):
        SafetyLevel("unknown")

# ---------------------------------------------------------------------------
# PluginListResponse model
# ---------------------------------------------------------------------------


class TestPluginListResponse:
    def test_required_fields(self):
        """Both required fields must be provided."""
        resp = PluginListResponse(
            plugins=[{"id": "nmap", "name": "Nmap"}],
            total=1,
        )
        assert len(resp.plugins) == 1
        assert resp.total == 1

    def test_total_reflects_plugins_length(self):
        """total should reflect the plugins list length."""
        plugins = [
            {"id": "nmap", "name": "Nmap"},
            {"id": "nuclei", "name": "Nuclei"},
        ]
        resp = PluginListResponse(plugins=plugins, total=2)
        assert resp.total == len(resp.plugins) == 2

    def test_empty_plugins_list(self):
        """Empty plugins list is valid."""
        resp = PluginListResponse(plugins=[], total=0)
        assert resp.plugins == []
        assert resp.total == 0

    def test_plugins_is_list_of_dicts(self):
        """plugins must be a list of dicts."""
        resp = PluginListResponse(
            plugins=[
                {"id": "nmap", "name": "Nmap", "version": "1.0"},
                {"id": "nikto", "name": "Nikto"},
            ],
            total=2,
        )
        assert all(isinstance(p, dict) for p in resp.plugins)
        assert resp.plugins[0]["id"] == "nmap"
        assert resp.plugins[1]["name"] == "Nikto"

    def test_total_can_be_zero(self):
        """total can be explicitly set to 0."""
        resp = PluginListResponse(plugins=[], total=0)
        assert resp.total == 0

    def test_total_accepts_any_int(self):
        """total accepts any non-negative integer."""
        resp = PluginListResponse(plugins=[], total=999)
        assert resp.total == 999
