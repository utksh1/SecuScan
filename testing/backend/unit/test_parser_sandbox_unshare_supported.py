"""
Unit tests for _unshare_net_supported in backend/secuscan/parser_sandbox.py.

Covers all distinct code paths:
1. Non-Linux platform returns False immediately
2. unshare binary not found returns False
3. unshare binary found but probe fails returns False
4. unshare binary found and probe succeeds returns True
"""

import sys
from unittest.mock import patch

import pytest

# The function can be imported directly; it does not pull in heavy dependencies.
from backend.secuscan.parser_sandbox import _unshare_net_supported


def _reset_module_globals():
    """Reset the module-level caching globals so each test starts clean."""
    import backend.secuscan.parser_sandbox as mod
    mod._unshare_capability_checked = False
    mod._unshare_available = None


class TestUnshareNetSupportedNonLinux:
    """Platform is not Linux: the function should return False without probing."""

    def test_returns_false_on_darwin(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Darwin"):
            result = _unshare_net_supported()
        assert result is False

    def test_returns_false_on_windows(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Windows"):
            result = _unshare_net_supported()
        assert result is False

    def test_caches_result_after_non_linux_call(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Darwin"):
            result1 = _unshare_net_supported()
        assert result1 is False
        # Subsequent calls return the cached _unshare_available value (False)
        result2 = _unshare_net_supported()
        assert result2 is False


class TestUnshareNetSupportedBinaryNotFound:
    """unshare binary is not in PATH: should return False."""

    def test_returns_false_when_which_returns_none(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value=None):
                result = _unshare_net_supported()
        assert result is False

    def test_caches_false_when_binary_not_found(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value=None):
                result1 = _unshare_net_supported()
        assert result1 is False
        # Second call uses cached _unshare_available from first call (False)
        result2 = _unshare_net_supported()
        assert result2 is False


class TestUnshareNetSupportedProbeFails:
    """unshare binary exists but the probe command fails (non-zero exit)."""

    def test_returns_false_when_probe_exit_nonzero(self):
        _reset_module_globals()
        mock_result = patch("backend.secuscan.parser_sandbox.subprocess.run")
        mock_result.return_value = mock_result
        mock_result.returncode = 1
        mock_result.return_value = type("MockResult", (), {"returncode": 1})()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run") as mock_run:
                    mock_run.return_value = type("Obj", (), {"returncode": 1})()
                    result = _unshare_net_supported()
        assert result is False

    def test_caches_false_when_probe_fails(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run") as mock_run:
                    mock_run.return_value = type("Obj", (), {"returncode": 1})()
                    result1 = _unshare_net_supported()
        assert result1 is False
        result2 = _unshare_net_supported()
        assert result2 is False


class TestUnshareNetSupportedProbeSucceeds:
    """unshare binary exists and the probe command succeeds (exit 0)."""

    def test_returns_true_when_probe_exit_zero(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run") as mock_run:
                    mock_run.return_value = type("Obj", (), {"returncode": 0})()
                    result = _unshare_net_supported()
        assert result is True

    def test_probes_with_correct_arguments(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/custom/path/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run") as mock_run:
                    mock_run.return_value = type("Obj", (), {"returncode": 0})()
                    _unshare_net_supported()
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    assert call_args[0] == "/custom/path/unshare"
                    assert "--user" in call_args
                    assert "--net" in call_args


class TestUnshareNetSupportedSubprocessException:
    """subprocess.run raises an exception (timeout, permission denied, etc.)."""

    def test_returns_false_when_subprocess_raises(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run") as mock_run:
                    mock_run.side_effect = OSError("permission denied")
                    result = _unshare_net_supported()
        assert result is False
