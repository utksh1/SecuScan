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
