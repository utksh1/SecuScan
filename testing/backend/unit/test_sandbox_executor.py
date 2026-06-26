"""
Unit tests for sandbox_executor.py pure helpers.

Covers (separately from testing/backend/test_sandbox_executor.py which tests
sandbox_execute end-to-end):
- classify_memory_violation: exit-code, stderr, and RSS threshold heuristics
- resolve_sandbox_config: global defaults merged with per-plugin overrides
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.secuscan.sandbox_executor import (
    _build_preexec_fn,
    classify_memory_violation,
    resolve_sandbox_config,
)
from backend.secuscan.models import SandboxConfig


# ---------------------------------------------------------------------------
# classify_memory_violation
# ---------------------------------------------------------------------------

class TestClassifyMemoryViolationExitCode:
    """Exit-code based memory violation detection."""

    def test_sigsegv_exit_code_negative_11_returns_true(self):
        """Exit code -11 (SIGSEGV) always indicates memory corruption."""
        assert classify_memory_violation(
            exit_code=-11, stderr_text="", rss_bytes=0, limit_bytes=100_000_000
        ) is True

    def test_sigsegv_exit_code_139_returns_true(self):
        """Exit code 139 (128+11 = SIGSEGV on Linux) always indicates memory corruption."""
        assert classify_memory_violation(
            exit_code=139, stderr_text="", rss_bytes=0, limit_bytes=100_000_000
        ) is True

    def test_exit_code_0_without_memory_signal_returns_false(self):
        """Exit code 0 without memory signal in stderr returns False."""
        assert classify_memory_violation(
            exit_code=0, stderr_text="", rss_bytes=0, limit_bytes=100_000_000
        ) is False

    def test_nonzero_exit_without_memory_signals_returns_false(self):
        """Non-zero exits without memory signals return False."""
        assert classify_memory_violation(
            exit_code=1, stderr_text=" segmentation fault", rss_bytes=0, limit_bytes=100_000_000
        ) is False


class TestClassifyMemoryViolationStderr:
    """Stderr-based memory violation detection."""

    def test_memoryerror_in_stderr_returns_true(self):
        """Python MemoryError in stderr indicates OOM."""
        assert classify_memory_violation(
            exit_code=1, stderr_text="MemoryError: cannot allocate", rss_bytes=0, limit_bytes=100_000_000
        ) is True

    def test_cannot_allocate_in_stderr_returns_true(self):
        """System 'Cannot allocate memory' message in stderr indicates OOM."""
        assert classify_memory_violation(
            exit_code=1, stderr_text="error: Cannot allocate memory", rss_bytes=0, limit_bytes=100_000_000
        ) is True

    def test_empty_stderr_with_nonzero_exit_returns_false(self):
        """Non-zero exit with no memory signal returns False (unless RSS threshold met)."""
        assert classify_memory_violation(
            exit_code=42, stderr_text="some unrelated error", rss_bytes=0, limit_bytes=100_000_000
        ) is False


class TestClassifyMemoryViolationRSS:
    """RSS-threshold based memory violation detection."""

    def test_rss_at_95_percent_with_nonzero_exit_returns_true(self):
        """RSS >= 95% of limit with non-zero exit is classified as OOM."""
        limit = 100_000_000  # 100 MB
        rss = limit * 95 // 100  # exactly 95%
        assert classify_memory_violation(
            exit_code=1, stderr_text="", rss_bytes=rss, limit_bytes=limit
        ) is True

    def test_rss_at_96_percent_with_nonzero_exit_returns_true(self):
        """RSS well above 95% threshold with non-zero exit is classified as OOM."""
        limit = 100_000_000
        rss = limit  # exactly at limit
        assert classify_memory_violation(
            exit_code=1, stderr_text="", rss_bytes=rss, limit_bytes=limit
        ) is True

    def test_rss_below_95_percent_with_nonzero_exit_returns_false(self):
        """RSS below 95% threshold with non-zero exit returns False."""
        limit = 100_000_000
        rss = limit * 94 // 100  # 94%
        assert classify_memory_violation(
            exit_code=1, stderr_text="", rss_bytes=rss, limit_bytes=limit
        ) is False

    def test_rss_threshold_ignored_on_successful_exit(self):
        """RSS threshold is only checked when exit_code is non-zero."""
        limit = 100_000_000
        rss = limit * 99 // 100  # 99% — but exit is 0
        assert classify_memory_violation(
            exit_code=0, stderr_text="", rss_bytes=rss, limit_bytes=limit
        ) is False


# ---------------------------------------------------------------------------
# resolve_sandbox_config
# ---------------------------------------------------------------------------

def test_resolve_sandbox_config_with_no_override():
    """When plugin_sandbox is None, returns a config from global settings."""
    from backend.secuscan import config as config_module

    mock_settings = MagicMock()
    mock_settings.sandbox_timeout = 120
    mock_settings.sandbox_memory_mb = 512
    mock_settings.sandbox_max_output_bytes = 5_000_000
    mock_settings.sandbox_allow_network = True

    original = config_module.settings
    config_module.settings = mock_settings
    try:
        config = resolve_sandbox_config(plugin_sandbox=None)
    finally:
        config_module.settings = original

    assert config.timeout_seconds == 120
    assert config.max_memory_mb == 512
    assert config.allow_network is True


def test_resolve_sandbox_config_partial_override():
    """Partial per-plugin override only changes the specified fields."""
    from backend.secuscan import config as config_module

    mock_settings = MagicMock()
    mock_settings.sandbox_timeout = 300
    mock_settings.sandbox_memory_mb = 512
    mock_settings.sandbox_max_output_bytes = 5_000_000
    mock_settings.sandbox_allow_network = True

    plugin_override = SandboxConfig(timeout_seconds=60)

    original = config_module.settings
    config_module.settings = mock_settings
    try:
        config = resolve_sandbox_config(plugin_sandbox=plugin_override)
    finally:
        config_module.settings = original

    assert config.timeout_seconds == 60
    assert config.max_memory_mb == 512
    assert config.allow_network is True


def test_resolve_sandbox_config_full_override():
    """Full per-plugin override replaces all global defaults."""
    from backend.secuscan import config as config_module

    mock_settings = MagicMock()
    mock_settings.sandbox_timeout = 300
    mock_settings.sandbox_memory_mb = 512
    mock_settings.sandbox_max_output_bytes = 5_000_000
    mock_settings.sandbox_allow_network = True

    plugin_override = SandboxConfig(
        timeout_seconds=30,
        max_memory_mb=256,
        max_output_bytes=1_000_000,
        allow_network=False,
    )

    original = config_module.settings
    config_module.settings = mock_settings
    try:
        config = resolve_sandbox_config(plugin_sandbox=plugin_override)
    finally:
        config_module.settings = original

    assert config.timeout_seconds == 30
    assert config.max_memory_mb == 256
    assert config.max_output_bytes == 1_000_000
    assert config.allow_network is False


# ---------------------------------------------------------------------------
# _build_preexec_fn
# ---------------------------------------------------------------------------


class TestBuildPreexecFn:
    """Tests for _build_preexec_fn."""

    def test_returns_callable(self):
        """_build_preexec_fn returns a callable."""
        config = SandboxConfig(max_memory_mb=256)
        fn = _build_preexec_fn(config)
        assert callable(fn)

    def test_does_not_raise_with_patched_resource(self):
        """The returned callable must not raise when resource.setrlimit is patched."""
        import resource as resource_module
        import sys

        mock_setrlimit = MagicMock()
        with patch.dict(sys.modules, {"resource": resource_module}):
            with patch.object(resource_module, "setrlimit", mock_setrlimit):
                config = SandboxConfig(max_memory_mb=256)
                fn = _build_preexec_fn(config)
                fn()  # Must not raise
                mock_setrlimit.assert_called_once()

    def test_sets_rlimit_as_to_memory_bytes(self):
        """The preexec_fn sets RLIMIT_AS to max_memory_mb * 1024 * 1024."""
        import resource as resource_module
        import sys

        mock_setrlimit = MagicMock()
        with patch.dict(sys.modules, {"resource": resource_module}):
            with patch.object(resource_module, "setrlimit", mock_setrlimit):
                config = SandboxConfig(max_memory_mb=128)
                fn = _build_preexec_fn(config)
                fn()
                call_args = mock_setrlimit.call_args
                assert call_args[0][0] == resource_module.RLIMIT_AS
                assert call_args[0][1] == (128 * 1024 * 1024, 128 * 1024 * 1024)
