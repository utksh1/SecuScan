"""
Unit tests for scripts/validate_plugins.py

Tests the pure helper functions: _results_to_dict, _print_result,
and build_parser.
"""

import argparse
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent / "scripts"))
from validate_plugins import _results_to_dict, _print_result, build_parser
from backend.secuscan.plugin_validator import ValidationResult


class TestResultsToDict:
    def test_empty_results(self):
        result = _results_to_dict([])
        assert result["summary"]["total"] == 0
        assert result["summary"]["passed"] == 0
        assert result["summary"]["failed"] == 0
        assert result["plugins"] == []

    def test_single_valid_result(self):
        vr = ValidationResult(
            plugin_id="nmap",
            plugin_dir=pathlib.Path("/repo/plugins/nmap"),
            errors=[],
        )
        d = _results_to_dict([vr])
        assert d["summary"]["total"] == 1
        assert d["summary"]["passed"] == 1
        assert d["summary"]["failed"] == 0
        assert len(d["plugins"]) == 1
        assert d["plugins"][0]["id"] == "nmap"
        assert d["plugins"][0]["valid"] is True

    def test_failed_result(self):
        from backend.secuscan.plugin_validator import ValidationError
        err = ValidationError(plugin_id="bad", path="metadata.json", message="missing field")
        vr = ValidationResult(
            plugin_id="bad",
            plugin_dir=pathlib.Path("/repo/plugins/bad"),
            errors=[err],
        )
        d = _results_to_dict([vr])
        assert d["summary"]["failed"] == 1
        assert d["summary"]["passed"] == 0
        assert d["plugins"][0]["valid"] is False

    def test_errors_serialized(self):
        vr = ValidationResult(
            plugin_id="bad",
            plugin_dir=pathlib.Path("/repo/plugins/bad"),
            errors=[],
        )
        d = _results_to_dict([vr])
        assert d["plugins"][0]["errors"] == []


class TestBuildParser:
    def test_returns_argument_parser(self):
        parser = build_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_prog_name_set(self):
        parser = build_parser()
        assert parser.prog == "validate_plugins"


class TestPrintResult:
    def test_valid_result_prints_plugin_id(self, capsys):
        vr = ValidationResult(
            plugin_id="nmap",
            plugin_dir=pathlib.Path("/repo/plugins/nmap"),
            errors=[],
        )
        _print_result(vr)
        out = capsys.readouterr().out
        assert "nmap" in out

    def test_invalid_result_prints_plugin_id(self, capsys):
        vr = ValidationResult(
            plugin_id="bad",
            plugin_dir=pathlib.Path("/repo/plugins/bad"),
            errors=[],
        )
        _print_result(vr)
        out = capsys.readouterr().out
        assert "bad" in out
