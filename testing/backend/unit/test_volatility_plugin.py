"""Unit tests for plugins/volatility/parser.py
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

PARSER_PATH = Path(__file__).resolve().parents[3] / "plugins" / "volatility" / "parser.py"


def _load_volatility_parser():
    spec = importlib.util.spec_from_file_location("volatility_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_volatility_parser_multiline_output_header_and_rows():
    parser = _load_volatility_parser()
    output = (
        "PID    PPID   ImageFileName\n"
        "4      0      System\n"
        "88     4      smss.exe\n"
        "352    344    csrss.exe\n"
    )
    parsed = parser.parse(output)

    assert parsed["count"] == 3
    assert len(parsed["findings"]) == 3

    first = parsed["findings"][0]
    assert first["title"] == "Volatility Artifact"
    assert first["category"] == "Memory Forensics"
    assert first["severity"] == "medium"
    assert first["description"] == "4      0      System"
    assert first["metadata"]["header"] == "PID    PPID   ImageFileName"
    assert first["metadata"]["row"] == "4      0      System"


def test_volatility_parser_empty_output():
    parser = _load_volatility_parser()
    parsed = parser.parse("")

    assert parsed == {"findings": [], "count": 0}


def test_volatility_parser_header_only_no_data_rows():
    parser = _load_volatility_parser()
    parsed = parser.parse("PID    PPID   ImageFileName\n")

    assert parsed["findings"] == []
    assert parsed["count"] == 0


def test_volatility_parser_more_than_25_rows_adds_truncation_finding():
    parser = _load_volatility_parser()
    header = "PID    PPID   ImageFileName"
    rows = [f"{100 + i}    1      proc{i}.exe" for i in range(30)]
    output = "\n".join([header] + rows)

    parsed = parser.parse(output)

    # 25 artifact findings + 1 truncation finding
    assert parsed["count"] == 26
    assert len(parsed["findings"]) == 26

    artifact_findings = [f for f in parsed["findings"] if f["title"] == "Volatility Artifact"]
    assert len(artifact_findings) == 25

    truncation = next(f for f in parsed["findings"] if f["title"] == "Volatility Output Truncated")
    assert truncation["category"] == "Memory Forensics"
    assert truncation["severity"] == "info"
    assert truncation["description"] == "Showing first 25 rows out of 30."
    assert truncation["metadata"]["total_rows"] == 30


def test_volatility_parser_exactly_25_rows_no_truncation_finding():
    parser = _load_volatility_parser()
    header = "PID    PPID   ImageFileName"
    rows = [f"{100 + i}    1      proc{i}.exe" for i in range(25)]
    output = "\n".join([header] + rows)

    parsed = parser.parse(output)

    assert parsed["count"] == 25
    assert len(parsed["findings"]) == 25
    assert all(f["title"] == "Volatility Artifact" for f in parsed["findings"])
    assert not any(f["title"] == "Volatility Output Truncated" for f in parsed["findings"])


def test_volatility_parser_whitespace_only_lines_are_skipped():
    parser = _load_volatility_parser()
    output = (
        "PID    PPID   ImageFileName\n"
        "   \n"
        "4      0      System\n"
        "\t\n"
        "   \t  \n"
        "88     4      smss.exe\n"
    )
    parsed = parser.parse(output)

    assert parsed["count"] == 2
    descriptions = [f["description"] for f in parsed["findings"]]
    assert descriptions == ["4      0      System", "88     4      smss.exe"]
    assert not any(d.strip() == "" for d in descriptions)
