"""Parser and contract coverage for plugins/scapy_recon."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Derive the plugins directory relative to this test file.
_PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
PARSER_PATH = _PLUGINS_DIR / "scapy_recon" / "parser.py"


def _load_scapy_recon_parser():
    spec = importlib.util.spec_from_file_location("scapy_recon_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_scapy_recon_multiple_up_lines():
    parser = _load_scapy_recon_parser()
    output = "UP: 192.168.1.1 - 00:11:22:33:44:55\nUP: 10.0.0.5 - aa:bb:cc:dd:ee:ff"
    parsed = parser.parse(output)
    assert parsed["count"] == 2
    assert len(parsed["findings"]) == 2
    assert len(parsed["hosts"]) == 2
    assert parsed["hosts"][0]["ip"] == "192.168.1.1"
    assert parsed["hosts"][0]["mac"] == "00:11:22:33:44:55"
    assert parsed["findings"][0]["metadata"]["ip"] == "192.168.1.1"
    assert parsed["findings"][0]["metadata"]["mac"] == "00:11:22:33:44:55"


def test_scapy_recon_single_up_line_with_mac():
    parser = _load_scapy_recon_parser()
    output = "UP: 172.16.0.10 - 00:1a:2b:3c:4d:5e"
    parsed = parser.parse(output)
    assert parsed["count"] == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Live Host Discovered: 172.16.0.10"
    assert finding["category"] == "Network Discovery"
    assert finding["severity"] == "info"
    assert finding["metadata"]["mac"] == "00:1a:2b:3c:4d:5e"


def test_scapy_recon_ip_only_no_mac():
    parser = _load_scapy_recon_parser()
    output = "UP: 192.168.1.100"
    parsed = parser.parse(output)
    assert parsed["count"] == 1
    assert parsed["hosts"][0]["ip"] == "192.168.1.100"
    assert parsed["hosts"][0]["mac"] == "Unknown"


def test_scapy_recon_non_up_lines_ignored():
    parser = _load_scapy_recon_parser()
    output = "ERROR: interface not found\nWARNING: no packets received\nUP: 10.0.0.1 - 00:00:00:11:22:33"
    parsed = parser.parse(output)
    assert parsed["count"] == 1
    assert parsed["findings"][0]["metadata"]["ip"] == "10.0.0.1"


def test_scapy_recon_empty_output():
    parser = _load_scapy_recon_parser()
    parsed = parser.parse("")
    assert parsed["count"] == 0
    assert parsed["findings"] == []
    assert parsed["hosts"] == []


def test_scapy_recon_no_up_prefix_lines():
    parser = _load_scapy_recon_parser()
    output = "scan started\ninterface: eth0\nscan complete"
    parsed = parser.parse(output)
    assert parsed["count"] == 0
    assert parsed["findings"] == []
