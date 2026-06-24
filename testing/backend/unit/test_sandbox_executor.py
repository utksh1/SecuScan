"""
Unit tests for sandbox_executor pure helper functions in
backend/secuscan/sandbox_executor.py.

Covers:
- resolve_sandbox_config: merges global settings with per-plugin overrides
- classify_memory_violation: post-mortem heuristic for memory exhaustion

sandbox_execute() performs real subprocess I/O and is NOT tested here.
_build_preexec_fn and _terminate_process touch process-level APIs;
they are tested only via the integration-level sandbox_execute() which is
out of scope for this file.
"""

import importlib
import sys
from unittest.mock import patch, MagicMock

import pytest

from backend.secuscan.sandbox_executor import classify_memory_violation


# ---------------------------------------------------------------------------
# resolve_sandbox_config
# ---------------------------------------------------------------------------

# resolve_sandbox_config imports settings via `from .config import settings`.
# Because sandbox_executor is already imported when this test file loads, the
# patch must be applied BEFORE the module under test reads settings.  We achieve
# this by patching sys.modules so that the next `import backend.secuscan.sandbox_executor`
# (via importlib.reload) sees the mock settings object.
_CONFIG_MODULE = "backend.secuscan.config"


class _FakeSettings:
    """Minimal plain object with the fields needed by resolve_sandbox_config."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def _reload_with_mock_settings(**settings_kwargs):
    """Reload sandbox_executor after patching config.settings in sys.modules."""
    fake_settings = _FakeSettings(**settings_kwargs)
    fake_config = MagicMock()
    fake_config.settings = fake_settings
    with patch.dict(sys.modules, {"backend.secuscan.config": fake_config}):
        import backend.secuscan.sandbox_executor as se
        importlib.reload(se)
        return se


class TestResolveSandboxConfig:
    def test_none_returns_settings_defaults(self):
        se = _reload_with_mock_settings(
            sandbox_timeout=600,
            sandbox_memory_mb=512,
            sandbox_max_output_bytes=5_242_880,
            sandbox_allow_network=True,
        )
        result = se.resolve_sandbox_config(None)
        assert result.timeout_seconds == 600
        assert result.max_memory_mb == 512
        assert result.max_output_bytes == 5_242_880
        assert result.allow_network is True

    def test_plugin_overrides_timeout_only(self):
        from backend.secuscan.models import SandboxConfig
        se = _reload_with_mock_settings(
            sandbox_timeout=600,
            sandbox_memory_mb=512,
            sandbox_max_output_bytes=5_242_880,
            sandbox_allow_network=True,
        )
        plugin_cfg = SandboxConfig(timeout_seconds=30)
        result = se.resolve_sandbox_config(plugin_cfg)
        # timeout_seconds is overridden; other fields get SandboxConfig defaults
        # which are 120 (timeout), 512 (memory), 5242880 (output), True (network)
        assert result.timeout_seconds == 30
        assert result.max_memory_mb == 512
        assert result.allow_network is True

    def test_plugin_overrides_memory_only(self):
        from backend.secuscan.models import SandboxConfig
        se = _reload_with_mock_settings(
            sandbox_timeout=600,
            sandbox_memory_mb=512,
            sandbox_max_output_bytes=5_242_880,
            sandbox_allow_network=True,
        )
        plugin_cfg = SandboxConfig(max_memory_mb=256)
        result = se.resolve_sandbox_config(plugin_cfg)
        # memory is overridden to 256; other fields use SandboxConfig defaults
        # (timeout=120, max_output=5242880, allow_network=True)
        assert result.max_memory_mb == 256
        assert result.timeout_seconds == 120

    def test_plugin_overrides_all_fields(self):
        from backend.secuscan.models import SandboxConfig
        se = _reload_with_mock_settings(
            sandbox_timeout=600,
            sandbox_memory_mb=512,
            sandbox_max_output_bytes=5_242_880,
            sandbox_allow_network=True,
        )
        plugin_cfg = SandboxConfig(
            timeout_seconds=30,
            max_memory_mb=256,
            max_output_bytes=1_048_576,
            allow_network=False,
        )
        result = se.resolve_sandbox_config(plugin_cfg)
        assert result.timeout_seconds == 30
        assert result.max_memory_mb == 256
        assert result.max_output_bytes == 1_048_576
        assert result.allow_network is False

    def test_all_none_plugin_cfg_returns_sandbox_config_defaults(self):
        from backend.secuscan.models import SandboxConfig
        se = _reload_with_mock_settings(
            sandbox_timeout=600,
            sandbox_memory_mb=512,
            sandbox_max_output_bytes=5_242_880,
            sandbox_allow_network=True,
        )
        # SandboxConfig() populates all fields with Pydantic defaults (not None),
        # so model_dump(exclude_none=True) returns all of them as overrides.
        # The result therefore uses SandboxConfig defaults throughout.
        plugin_cfg = SandboxConfig()
        result = se.resolve_sandbox_config(plugin_cfg)
        assert result.timeout_seconds == 120
        assert result.max_memory_mb == 512


# ---------------------------------------------------------------------------
# classify_memory_violation
# ---------------------------------------------------------------------------


class TestClassifyMemoryViolation:
    def test_sigsegv_minus_11(self):
        assert classify_memory_violation(-11, "", 0, 512 * 1024 * 1024) is True

    def test_sigsegv_139(self):
        assert classify_memory_violation(139, "", 0, 512 * 1024 * 1024) is True

    def test_memory_error_in_stderr(self):
        assert classify_memory_violation(1, "Fatal Python error: MemoryError", 0, 512 * 1024 * 1024) is True

    def test_cannot_allocate_in_stderr(self):
        assert classify_memory_violation(1, "OSError: Cannot allocate memory", 0, 512 * 1024 * 1024) is True

    def test_rss_at_95_percent_and_non_zero_exit(self):
        limit = 512 * 1024 * 1024
        rss = limit * 95 // 100
        assert classify_memory_violation(1, "", rss, limit) is True

    def test_rss_at_96_percent_and_non_zero_exit(self):
        limit = 512 * 1024 * 1024
        rss = limit * 96 // 100
        assert classify_memory_violation(1, "", rss, limit) is True

    def test_rss_below_95_percent_non_zero_exit(self):
        limit = 512 * 1024 * 1024
        rss = limit * 94 // 100
        assert classify_memory_violation(1, "", rss, limit) is False

    def test_zero_exit_code_returns_false_even_high_rss(self):
        limit = 512 * 1024 * 1024
        rss = limit
        assert classify_memory_violation(0, "", rss, limit) is False

    def test_memory_error_in_stderr_triggers_true_regardless_of_exit_code(self):
        assert classify_memory_violation(0, "MemoryError in subprocess", 0, 512 * 1024 * 1024) is True

    def test_non_sigsegv_exit_low_rss_zero_exit(self):
        assert classify_memory_violation(2, "some error", 1000, 512 * 1024 * 1024) is False

    def test_cannot_allocate_triggered_true_despite_low_rss(self):
        assert classify_memory_violation(1, "Cannot allocate memory", 1000, 512 * 1024 * 1024) is True