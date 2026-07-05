"""Parser and contract coverage for plugins/sqlmap."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Derive the plugins directory relative to this test file.
_PLUGINS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "plugins"
PARSER_PATH = _PLUGINS_DIR / "sqlmap" / "parser.py"


def _load_sqlmap_parser():
    spec = importlib.util.spec_from_file_location("sqlmap_parser", PARSER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sqlmap_parser_named_parameter_injection():
    parser = _load_sqlmap_parser()
    output = "Parameter: userId (GET) is vulnerable"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "SQL Injection Vulnerability: userId"
    assert finding["severity"] == "critical"
    assert finding["metadata"]["parameter"] == "userId"
    assert finding["metadata"]["type"] == "GET"


def test_sqlmap_parser_unspecified_injection():
    parser = _load_sqlmap_parser()
    output = "Target is vulnerable but the parameter could not be identified"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 1
    finding = parsed["findings"][0]
    assert finding["title"] == "Unspecified SQL Injection Vulnerability"
    assert finding["severity"] == "critical"


def test_sqlmap_parser_back_end_dbms_metadata():
    parser = _load_sqlmap_parser()
    output = "back-end DBMS: PostgreSQL 14.3\nsome other output"
    parsed = parser.parse(output)
    assert parsed["metadata"]["dbms"] == "PostgreSQL 14.3"


def test_sqlmap_parser_web_tech_metadata():
    parser = _load_sqlmap_parser()
    output = "web application technology: PHP 8.0, Nginx 1.20\nsome other output"
    parsed = parser.parse(output)
    assert parsed["metadata"]["tech_stack"] == "PHP 8.0, Nginx 1.20"


def test_sqlmap_parser_clean_output_no_findings():
    parser = _load_sqlmap_parser()
    output = "starting sqlmap 1.7\n[INFO] scan complete"
    parsed = parser.parse(output)
    assert len(parsed["findings"]) == 0


def test_sqlmap_parser_empty_output():
    parser = _load_sqlmap_parser()
    parsed = parser.parse("")
    assert len(parsed["findings"]) == 0
