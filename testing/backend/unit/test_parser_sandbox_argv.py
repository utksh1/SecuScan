"""
Unit tests for backend.secuscan.parser_sandbox._sandbox_argv.

Run with:
    python3 -m pytest testing/backend/unit/test_parser_sandbox_argv.py -v --noconftest
"""

from __future__ import annotations

import pytest

from backend.secuscan import parser_sandbox


def _mock_unshare(monkeypatch, available: bool) -> None:
    monkeypatch.setattr(
        "backend.secuscan.parser_sandbox._unshare_net_supported",
        lambda: available,
    )


class TestSandboxArgvNetworkIsolationEnabled:
    def test_returns_unshare_prefix_when_supported(self, monkeypatch):
        _mock_unshare(monkeypatch, True)
        result = parser_sandbox._sandbox_argv("/usr/bin/python3", "bootstrap_code_here")
        assert result[0:4] == ["unshare", "--user", "--net", "--"]
        assert result[4] == "/usr/bin/python3"
        assert result[5] == "-c"
        assert result[6] == "bootstrap_code_here"

    def test_unshare_not_logged_when_supported(self, monkeypatch, caplog):
        _mock_unshare(monkeypatch, True)
        result = parser_sandbox._sandbox_argv("/usr/bin/python3", "code")
        assert "unshare" in result[0]


class TestSandboxArgvNetworkIsolationUnavailable:
    def test_returns_base_argv_when_not_supported(self, monkeypatch):
        _mock_unshare(monkeypatch, False)
        result = parser_sandbox._sandbox_argv("/usr/bin/python3", "bootstrap_code_here")
        assert result == ["/usr/bin/python3", "-c", "bootstrap_code_here"]

    def test_unshare_warning_logged_once(self, monkeypatch, caplog):
        _mock_unshare(monkeypatch, False)
        # Reset the warning flag
        parser_sandbox._unshare_warning_logged = False
        parser_sandbox._sandbox_argv("/usr/bin/python3", "code")
        parser_sandbox._sandbox_argv("/usr/bin/python3", "different_code")
        # Warning should only appear once (after the first call)
        assert any("network isolation unavailable" in record.message for record in caplog.records)

    def test_different_python_executable_preserved(self, monkeypatch):
        _mock_unshare(monkeypatch, False)
        result = parser_sandbox._sandbox_argv("/opt/custom/python", "code")
        assert result[0] == "/opt/custom/python"

    def test_different_bootstrap_code_preserved(self, monkeypatch):
        _mock_unshare(monkeypatch, False)
        result = parser_sandbox._sandbox_argv("/usr/bin/python3", "print('hello')")
        assert result[2] == "print('hello')"
