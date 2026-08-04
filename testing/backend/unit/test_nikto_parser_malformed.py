"""Malformed-output and fallback-path tests for plugins/nikto/parser.py (issue #1420)."""

from __future__ import annotations

import json

import pytest

from plugins.nikto.parser import parse


def _assert_stable_text_shape(parsed: dict, raw: str) -> None:
    assert isinstance(parsed, dict)
    assert "findings" in parsed
    assert "count" in parsed
    assert "metadata" in parsed
    assert "summary" in parsed
    assert isinstance(parsed["findings"], list)
    assert isinstance(parsed["metadata"], dict)
    assert isinstance(parsed["summary"], list)
    assert parsed["count"] == len(parsed["findings"])
    if not parsed["findings"]:
        assert parsed["raw"] == raw


def _assert_stable_json_shape(parsed: dict) -> None:
    assert isinstance(parsed, dict)
    assert "findings" in parsed
    assert "count" in parsed
    assert "target" in parsed
    assert isinstance(parsed["findings"], list)
    assert parsed["count"] == len(parsed["findings"])


@pytest.mark.parametrize(
    "raw_output",
    [
        "",
        "   \n\n   ",
        "{}",
        '{"vulnerabilities": []}',
        "[]",
        '{"findings": null, "vulnerabilities": null}',
    ],
)
def test_nikto_parser_empty_outputs_return_stable_structure(raw_output: str):
    parsed = parse(raw_output)

    if raw_output.strip().startswith(("{", "[")):
        _assert_stable_json_shape(parsed)
        assert parsed["findings"] == []
        assert parsed["count"] == 0
        assert parsed["raw"] == raw_output
    else:
        _assert_stable_text_shape(parsed, raw_output)
        assert parsed["findings"] == []
        assert parsed["count"] == 0


def test_nikto_parser_json_malformed_numeric_and_port_fields():
    payload = {
        "host": "example.com",
        "port": "not-a-port",
        "vulnerabilities": [
            {
                "id": None,
                "osvdb": 12345,
                "msg": "Missing security header on port abc",
                "url": "/",
                "method": "GET",
            }
        ],
    }
    raw_output = json.dumps(payload)
    parsed = parse(raw_output)

    _assert_stable_json_shape(parsed)
    assert parsed["count"] == 1
    assert parsed["target"] == "example.com"
    finding = parsed["findings"][0]
    assert finding["title"] == "Missing security header on port abc"
    assert finding["metadata"]["osvdb"] == 12345
    assert "id" not in finding["metadata"]


def test_nikto_parser_text_malformed_port_field_is_preserved():
    raw_output = (
        "- Nikto v2.5.0\n"
        "---------------------------------------------------------------------------\n"
        "+ Target IP:          192.168.1.1\n"
        "+ Target Hostname:    example.com\n"
        "+ Target Port:        not-a-port\n"
        "---------------------------------------------------------------------------\n"
        "+ 0 host(s) tested\n"
    )
    parsed = parse(raw_output)

    _assert_stable_text_shape(parsed, raw_output)
    assert parsed["metadata"]["target_ip"] == "192.168.1.1"
    assert parsed["metadata"]["target_hostname"] == "example.com"
    assert parsed["metadata"]["target_port"] == "not-a-port"
    assert parsed["count"] == 1
    assert parsed["findings"][0]["title"] == "0 host(s) tested"


def test_nikto_parser_text_partial_output_with_metadata_only():
    raw_output = (
        "- Nikto v2.5.0\n"
        "---------------------------------------------------------------------------\n"
        "+ Target IP:          10.0.0.5\n"
        "+ Target Hostname:    scan.example\n"
        "+ Start Time:         2026-07-08 10:00:00\n"
        "+ End Time:           2026-07-08 10:01:00\n"
        "+ 12 requests: 0 error(s) and 0 item(s) reported on remote host\n"
        "---------------------------------------------------------------------------\n"
    )
    parsed = parse(raw_output)

    _assert_stable_text_shape(parsed, raw_output)
    assert parsed["findings"] == []
    assert parsed["count"] == 0
    assert parsed["metadata"]["target_ip"] == "10.0.0.5"
    assert parsed["metadata"]["target_hostname"] == "scan.example"
    assert len(parsed["summary"]) == 1
    assert "0 item(s) reported" in parsed["summary"][0]


def test_nikto_parser_json_partial_vulnerability_uses_defaults():
    raw_output = json.dumps(
        {
            "vulnerabilities": [
                {"msg": "Directory indexing enabled"},
                {},
                "not-a-dict",
                {"description": None, "url": "", "method": None},
            ]
        }
    )
    parsed = parse(raw_output)

    _assert_stable_json_shape(parsed)
    assert parsed["count"] == 3
    assert parsed["findings"][0]["title"] == "Directory indexing enabled"
    assert parsed["findings"][1]["title"] == "Nikto finding"
    assert parsed["findings"][2]["title"] == "Nikto finding"


def test_nikto_parser_invalid_json_falls_back_to_text_without_raising():
    raw_output = (
        "Nikto scan warning: output may be incomplete\n"
        '{"vulnerabilities": [\n'
        '  {"id": "1", "msg": "Truncated"\n'
    )
    parsed = parse(raw_output)

    _assert_stable_text_shape(parsed, raw_output)
    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_nikto_parser_embedded_json_block_fallback_extracts_findings():
    raw_output = (
        "Starting Nikto wrapper\n"
        '{"vulnerabilities": [{"msg": "Cookie missing HttpOnly flag", "url": "/"}]}\n'
        "Scan complete.\n"
    )
    parsed = parse(raw_output)

    _assert_stable_json_shape(parsed)
    assert parsed["count"] == 1
    assert parsed["findings"][0]["title"] == "Cookie missing HttpOnly flag"
    assert parsed["findings"][0]["category"] == "Cookie Security"
    assert parsed["raw"] is None


def test_nikto_parser_garbage_input_does_not_raise():
    raw_output = "asdf ###!!! random noise 12345 not nikto output at all"
    parsed = parse(raw_output)

    _assert_stable_text_shape(parsed, raw_output)
    assert parsed["findings"] == []
    assert parsed["count"] == 0


@pytest.mark.parametrize(
    "raw_output",
    [
        "",
        "not json",
        '{"broken": ',
        "+ Target Port:\n",
        json.dumps({"vulnerabilities": [{"msg": "test", "osvdb": "bad-id"}]}),
        json.dumps([{"msg": "list item"}]),
    ],
)
def test_nikto_parser_never_raises_on_malformed_inputs(raw_output: str):
    parsed = parse(raw_output)
    assert isinstance(parsed, dict)
    assert "findings" in parsed
    assert "count" in parsed
    assert parsed["count"] == len(parsed["findings"])
