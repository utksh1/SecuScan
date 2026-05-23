import json
from unittest.mock import MagicMock, patch

MOCK_SETTINGS = MagicMock()
MOCK_SETTINGS.task_start_max_body_bytes = 64_000
MOCK_SETTINGS.task_start_max_field_length = 1_000
MOCK_SETTINGS.task_start_max_array_length = 50

with patch("backend.secuscan.validation.settings", MOCK_SETTINGS):
    from backend.secuscan.validation import validate_task_start_payload

MAX_BYTES = MOCK_SETTINGS.task_start_max_body_bytes
MAX_FIELD = MOCK_SETTINGS.task_start_max_field_length
MAX_ARRAY = MOCK_SETTINGS.task_start_max_array_length

def _encode(p): return json.dumps(p).encode()

def test_normal_payload_passes():
    p = {"plugin_id":"nmap","inputs":{"target":"192.168.1.1"}}
    ok,code,msg = validate_task_start_payload(_encode(p),p["inputs"])
    assert ok and code==0

def test_oversized_body_returns_413():
    p = {"plugin_id":"nmap","inputs":{"x":"a"*(MAX_BYTES+1)}}
    ok,code,msg = validate_task_start_payload(_encode(p),p["inputs"])
    assert not ok and code==413

def test_oversized_string_field_returns_400():
    p = {"plugin_id":"nmap","inputs":{"target":"a"*(MAX_FIELD+1)}}
    ok,code,msg = validate_task_start_payload(_encode(p),p["inputs"])
    assert not ok and code==400

def test_oversized_array_returns_400():
    p = {"plugin_id":"nmap","inputs":{"ports":["80"]*(MAX_ARRAY+1)}}
    ok,code,msg = validate_task_start_payload(_encode(p),p["inputs"])
    assert not ok and code==400
