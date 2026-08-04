"""
Unit tests for _unshare_net_supported in backend/secuscan/parser_sandbox.py.

The parser_sandbox module is importable without conftest fixtures since it only
depends on platform, shutil, and subprocess (all stdlib).
"""
from unittest.mock import patch, MagicMock
import pytest

from backend.secuscan.parser_sandbox import _unshare_net_supported


def _reset_module_globals():
    """Reset module-level cache so the function re-evaluates on next call."""
    import backend.secuscan.parser_sandbox as mod
    mod._unshare_capability_checked = False
    mod._unshare_available = False


# ---------------------------------------------------------------------------
# Non-Linux paths
# ---------------------------------------------------------------------------

class TestUnshareNetSupportedNonLinux:
    """On non-Linux platforms, _unshare_net_supported returns False."""

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
        """Subsequent calls must not re-evaluate — must return cached value."""
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Darwin"):
            result1 = _unshare_net_supported()
        assert result1 is False
        result2 = _unshare_net_supported()
        assert result2 is False


# ---------------------------------------------------------------------------
# Linux path: shutil.which returns None
# ---------------------------------------------------------------------------

class TestUnshareNetSupportedBinaryNotFound:
    """If the unshare binary is not in PATH, return False and cache it."""

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
        result2 = _unshare_net_supported()
        assert result2 is False


# ---------------------------------------------------------------------------
# Linux path: subprocess.run probe fails
# ---------------------------------------------------------------------------

class TestUnshareNetSupportedProbeFails:
    """If the unshare probe exits non-zero, return False."""

    def test_returns_false_when_probe_exit_nonzero(self):
        _reset_module_globals()
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run", return_value=mock_proc):
                    result = _unshare_net_supported()
        assert result is False

    def test_caches_false_when_probe_fails(self):
        _reset_module_globals()
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run", return_value=mock_proc):
                    result1 = _unshare_net_supported()
        assert result1 is False
        result2 = _unshare_net_supported()
        assert result2 is False


# ---------------------------------------------------------------------------
# Linux path: subprocess.run probe succeeds
# ---------------------------------------------------------------------------

class TestUnshareNetSupportedProbeSucceeds:
    """If the unshare probe exits 0, return True."""

    def test_returns_true_when_probe_exit_zero(self):
        _reset_module_globals()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run", return_value=mock_proc):
                    result = _unshare_net_supported()
        assert result is True

    def test_probes_with_correct_arguments(self):
        _reset_module_globals()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run", return_value=mock_proc) as mock_run:
                    _unshare_net_supported()
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert kwargs.get("capture_output") is True
        assert kwargs.get("timeout") == 5


# ---------------------------------------------------------------------------
# Linux path: subprocess raises an exception
# ---------------------------------------------------------------------------

class TestUnshareNetSupportedSubprocessException:
    """If subprocess.run raises an exception, return False."""

    def test_returns_false_when_subprocess_raises(self):
        _reset_module_globals()
        with patch("backend.secuscan.parser_sandbox.platform.system", return_value="Linux"):
            with patch("backend.secuscan.parser_sandbox.shutil.which", return_value="/usr/bin/unshare"):
                with patch("backend.secuscan.parser_sandbox.subprocess.run",
                           side_effect=OSError("exec failed")):
                    result = _unshare_net_supported()
        assert result is False
