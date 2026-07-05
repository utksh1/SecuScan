"""Parser and contract coverage for plugins/volatility."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Derive the plugins directory relative to this test file.
_PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
PARSER_PATH = _PLUGINS_DIR / "volatility" / "parser.py"


def _load_volatility_parser():
    spec = importlib.util.spec_from_file_location("volatility_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_volatility_parser_multiple_rows():
    parser = _load_volatility_parser()
    output = "PID    Name    ImageBase\n100    explorer    0x00a00000\n200    svchost    0x00b00000\n300    chrome    0x00c00000"
    parsed = parser.parse(output)
    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3
    assert parsed["findings"][0]["category"] == "Memory Forensics"
    assert parsed["findings"][0]["severity"] == "medium"
    assert parsed["findings"][0]["metadata"]["header"] == "PID    Name    ImageBase"
    assert parsed["findings"][0]["metadata"]["row"] == "100    explorer    0x00a00000"


def test_volatility_parser_empty_output():
    parser = _load_volatility_parser()
    parsed = parser.parse("")
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_volatility_parser_header_only():
    parser = _load_volatility_parser()
    output = "PID    Name    ImageBase"
    parsed = parser.parse(output)
    assert parsed["count"] == 0
    assert parsed["findings"] == []


def test_volatility_parser_more_than_25_rows():
    parser = _load_volatility_parser()
    header = "Offset    PID    Name"
    rows = "\n".join(f"{i*0x1000:08x}    {100+i}    proc_{100+i}" for i in range(1, 31))
    output = header + "\n" + rows
    parsed = parser.parse(output)
    assert parsed["count"] == 26  # 25 artifact rows + 1 truncation row
    assert len(parsed["findings"]) == 26
    # The last finding should be the truncation notice
    truncation_finding = parsed["findings"][-1]
    assert truncation_finding["title"] == "Volatility Output Truncated"
    assert truncation_finding["metadata"]["total_rows"] == 30


def test_volatility_parser_exactly_25_rows():
    parser = _load_volatility_parser()
    header = "Offset    PID    Name"
    rows = "\n".join(f"{i*0x1000:08x}    {i}    proc_{i}" for i in range(1, 26))
    output = header + "\n" + rows
    parsed = parser.parse(output)
    assert parsed["count"] == 25
    # No truncation finding since exactly 25 rows
    titles = [f["title"] for f in parsed["findings"]]
    assert "Volatility Output Truncated" not in titles


def test_volatility_parser_whitespace_only_lines_skipped():
    parser = _load_volatility_parser()
    output = "Offset    PID\n  \n  \n0x1000    100"
    parsed = parser.parse(output)
    # Only the actual data row should be a finding, whitespace lines skipped
    assert parsed["count"] == 1
    assert parsed["findings"][0]["metadata"]["row"] == "0x1000    100"
