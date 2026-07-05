"""Parser and contract coverage for plugins/ssh_runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Derive the plugins directory relative to this test file.
_PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
PARSER_PATH = _PLUGINS_DIR / "ssh_runner" / "parser.py"


def _load_ssh_runner_parser():
    spec = importlib.util.spec_from_file_location("ssh_runner_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ssh_runner_clean_output():
    parser = _load_ssh_runner_parser()
    output = "Disk usage: 45%\nMemory: 2.1 GB free"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "SSH Command Executed Successfully"
    assert finding["severity"] == "info"
    assert finding["category"] == "Remote Execution"
    assert parsed["raw_output"] == output


def test_ssh_runner_permission_denied():
    parser = _load_ssh_runner_parser()
    output = "Permission denied for user admin"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "SSH Execution Failed / Error"
    assert finding["severity"] == "medium"


def test_ssh_runner_connection_refused():
    parser = _load_ssh_runner_parser()
    output = "ssh: connect to host 10.0.0.1 port 22: Connection refused"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "SSH Execution Failed / Error"
    assert finding["severity"] == "medium"


def test_ssh_runner_both_failure_indicators():
    parser = _load_ssh_runner_parser()
    output = "Permission denied\nConnection refused"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "SSH Execution Failed / Error"
    assert finding["severity"] == "medium"


def test_ssh_runner_empty_output():
    parser = _load_ssh_runner_parser()
    parsed = parser.parse("")
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    # Empty output still produces the default successful-info finding
    assert finding["title"] == "SSH Command Executed Successfully"
    assert finding["severity"] == "info"
