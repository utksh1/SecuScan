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
