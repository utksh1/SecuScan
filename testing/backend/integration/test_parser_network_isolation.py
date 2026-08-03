"""
Regression coverage for issue #1620: parser subprocess network isolation.
Malicious plugin parsers previously inherited the parent's full network
stack and could exfiltrate scan data to attacker-controlled servers.
This module verifies the network isolation mechanism works.
"""

import json
import subprocess
from pathlib import Path
import tempfile
import pytest

from backend.secuscan.parser_sandbox import (
    _unshare_net_supported,
    _sandbox_argv,
    run_parser_in_sandbox,
)


def test_unshare_capability_probe_returns_bool():
    # Probe should always return a boolean; on non-Linux or missing util-linux,
    # it's False, but it doesn't crash.
    result = _unshare_net_supported()
    assert isinstance(result, bool)


def test_sandbox_argv_without_isolation_on_non_linux(monkeypatch):
    # On non-Linux (or if unshare is unavailable), _sandbox_argv still returns
    # a valid argv; it just doesn't prepend unshare.
    monkeypatch.setattr(
        "backend.secuscan.parser_sandbox._unshare_net_supported",
        lambda: False,
    )
    argv = _sandbox_argv("python3", "print('test')")
    assert argv == ["python3", "-c", "print('test')"]


def test_sandbox_argv_with_isolation_on_linux(monkeypatch):
    # If network isolation is available, argv is prepended with unshare.
    monkeypatch.setattr(
        "backend.secuscan.parser_sandbox._unshare_net_supported",
        lambda: True,
    )
    argv = _sandbox_argv("python3", "print('test')")
    assert argv[0:3] == ["unshare", "--user", "--net"]
    assert argv[-2:] == ["-c", "print('test')"]


def test_parser_runs_successfully_with_isolation():
    # Even with network isolation in place, a normal parser.py works fine.
    # The parser only needs to transform text, not network.
    with tempfile.TemporaryDirectory() as tmpdir:
        parser_file = Path(tmpdir) / "parser.py"
        parser_file.write_text(
            """
def parse(input_data):
    lines = input_data.strip().split('\\n')
    return {
        'findings': [
            {'title': f'Finding {i}', 'severity': 'info'}
            for i in range(len(lines))
        ]
    }
"""
        )

        result = run_parser_in_sandbox(
            parser_file,
            "test_plugin",
            "line1\nline2\nline3",
        )

        assert result["findings"][0]["title"] == "Finding 0"
        assert len(result["findings"]) == 3
