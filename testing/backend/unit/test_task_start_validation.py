import json, pytest
from unittest.mock import patch, MagicMock

MOCK_SETTINGS = MagicMock()
MOCK_SETTINGS.task_start_max_body_bytes = 64_000
MOCK_SETTINGS.task_start_max_field_length = 1_000
MOCK_SETTINGS.task_start_max_array_length = 50

with patch("backend.secuscan.validation.settings", MOCK_SETTINGS):
    from backend.secuscan.validation import validate_task_start_payload

MAX_BYTES = MOCK_SETTINGS.task_start_max_body_bytes
MAX_FIELD = MOCK_SETTINGS.task_start_max_field_length
MAX_ARRAY = MOCK_SETTINGS.task_start_max_array_length


def _encode(p):
    return json.dumps(p).encode()


def test_normal_payload_passes():
    p = {"plugin_id": "nmap", "inputs": {"target": "192.168.1.1"}}
    ok, code, msg = validate_task_start_payload(_encode(p), p["inputs"])
    assert ok and code == 0


def test_oversized_body_returns_413():
    p = {"plugin_id": "nmap", "inputs": {"x": "a" * (MAX_BYTES + 1)}}
    ok, code, msg = validate_task_start_payload(_encode(p), p["inputs"])
    assert not ok and code == 413


def test_oversized_string_field_returns_400():
    p = {"plugin_id": "nmap", "inputs": {"target": "a" * (MAX_FIELD + 1)}}
    ok, code, msg = validate_task_start_payload(_encode(p), p["inputs"])
    assert not ok and code == 400


def test_oversized_array_returns_400():
    p = {"plugin_id": "nmap", "inputs": {"ports": ["80"] * (MAX_ARRAY + 1)}}
    ok, code, msg = validate_task_start_payload(_encode(p), p["inputs"])
    assert not ok and code == 400


def test_inputs_not_a_dict_returns_400():
    # inputs must be a JSON object, not a list or string
    ok, code, msg = validate_task_start_payload(b"[]", [])
    assert not ok and code == 400
    assert "inputs" in msg.lower()


def test_array_item_too_long_returns_400():
    inputs = {"ports": ["80", "a" * (MAX_FIELD + 1)]}
    ok, code, msg = validate_task_start_payload(_encode({"inputs": inputs}), inputs)
    assert not ok and code == 400


def test_non_string_field_values_pass():
    # Integer and boolean values in inputs are allowed — only strings/lists are length-checked
    inputs = {"timeout": 30, "verbose": True, "count": None}
    ok, code, msg = validate_task_start_payload(_encode({"inputs": inputs}), inputs)
    assert ok and code == 0


def test_field_at_exact_max_length_passes():
    # Boundary: exactly MAX_FIELD chars must pass
    inputs = {"target": "a" * MAX_FIELD}
    ok, code, msg = validate_task_start_payload(_encode({"inputs": inputs}), inputs)
    assert ok and code == 0


def test_error_message_does_not_echo_field_value():
    # Security: oversized field value must not appear in the error message
    secret_value = "SECRET_" + "x" * (MAX_FIELD + 1)
    inputs = {"target": secret_value}
    ok, code, msg = validate_task_start_payload(_encode({"inputs": inputs}), inputs)
    assert not ok
    assert "SECRET_" not in msg
    assert secret_value not in msg
