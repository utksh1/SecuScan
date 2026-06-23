import pytest
from pydantic import ValidationError
from backend.secuscan.models import TaskCreateRequest, PluginField, PluginFieldType

def test_task_create_request_valid():
    # Valid request
    req = TaskCreateRequest(
        plugin_id="http_inspector",
        inputs={"url": "http://example.com"},
        consent_granted=True
    )
    assert req.plugin_id == "http_inspector"
    assert req.consent_granted is True
    assert req.inputs["url"] == "http://example.com"

def test_task_create_request_missing_fields():
    # Missing required 'plugin_id' and 'inputs'
    with pytest.raises(ValidationError):
        TaskCreateRequest(consent_granted=True)

def test_plugin_field_valid():
    field = PluginField(
        id="timeout",
        label="Timeout",
        type=PluginFieldType.INTEGER,
        required=False,
        default=10
    )
    assert field.id == "timeout"
    assert field.default == 10
    assert field.type == PluginFieldType.INTEGER


import pytest
from pydantic import ValidationError
from backend.secuscan.models import (
    Finding,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    BulkDeleteRequest,
    NotificationSeverityThreshold,
    NotificationChannelType,
    FindingKind,
    AnalystStatus,
)


# Finding model tests

def test_finding_full_construction():
    finding = Finding(
        title="SQL Injection in /login",
        category="Injection",
        severity="high",
        target="https://app.example.com",
        description="User input is directly used in SQL query",
        remediation="Use parameterized queries",
        cve="CVE-2024-12345",
        cvss=8.2,
        confidence=0.9,
        validated=True,
        validation_method="payload_verification",
        evidence=[{"type": "request", "value": "id=1 OR 1=1"}],
        asset_refs=["asset-1", "asset-2"],
        references=[{"url": "https://owasp.org"}],
    )
    assert finding.title == "SQL Injection in /login"
    assert finding.severity == "high"
    assert finding.cve == "CVE-2024-12345"
    assert finding.confidence == 0.9
    assert finding.validated is True
    assert len(finding.evidence) == 1
    # finding_kind defaults to OBSERVATION in the model; normalization sets it
    assert finding.finding_kind == FindingKind.OBSERVATION


def test_finding_defaults():
    finding = Finding(
        title="Open Port Detected",
        category="Network",
        severity="info",
        target="https://example.com",
        description="Port 22 is open",
    )
    assert finding.validated is False
    assert finding.occurrence_count == 1
    assert finding.evidence_count == 0
    assert finding.analyst_status == AnalystStatus.NEW
    assert finding.finding_kind == FindingKind.OBSERVATION


def test_finding_analyst_status_enum():
    assert AnalystStatus.NEW == "new"
    assert AnalystStatus.CONFIRMED == "confirmed"
    assert AnalystStatus.FALSE_POSITIVE == "false_positive"


# NotificationRuleCreate tests

def test_notification_rule_create_valid():
    rule = NotificationRuleCreate(
        name="Critical Webhook",
        severity_threshold=NotificationSeverityThreshold.CRITICAL,
        channel_type=NotificationChannelType.WEBHOOK,
        target_url_or_email="https://hooks.example.com/alert",
    )
    assert rule.name == "Critical Webhook"
    assert rule.severity_threshold == NotificationSeverityThreshold.CRITICAL
    assert rule.is_active is True


def test_notification_rule_create_requires_name():
    # name is a required str field
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            severity_threshold=NotificationSeverityThreshold.HIGH,
            channel_type=NotificationChannelType.WEBHOOK,
            target_url_or_email="https://hooks.example.com",
        )


def test_notification_rule_create_requires_channel_type():
    with pytest.raises(ValidationError):
        NotificationRuleCreate(
            name="Rule",
            severity_threshold=NotificationSeverityThreshold.HIGH,
            target_url_or_email="https://hooks.example.com",
        )


# NotificationRuleUpdate tests

def test_notification_rule_update_partial_fields():
    update = NotificationRuleUpdate(name="Updated Name")
    assert update.name == "Updated Name"
    assert update.severity_threshold is None
    assert update.is_active is None


def test_notification_rule_update_all_none_is_valid():
    update = NotificationRuleUpdate()
    assert update.name is None


# BulkDeleteRequest tests

def test_bulk_delete_request_valid():
    ids = [f"task-{i}" for i in range(10)]
    req = BulkDeleteRequest.model_validate(ids)
    assert len(req.root) == 10


def test_bulk_delete_request_empty_is_valid():
    req = BulkDeleteRequest.model_validate([])
    assert len(req.root) == 0
