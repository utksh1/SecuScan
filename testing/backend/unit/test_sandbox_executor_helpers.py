"""
Unit tests for sandbox_executor.py helper functions.

Covers: resolve_sandbox_config, classify_memory_violation, _build_preexec_fn.
"""

import platform
from unittest.mock import patch

import pytest

from backend.secuscan.sandbox_executor import (
    resolve_sandbox_config,
    classify_memory_violation,
    _build_preexec_fn,
)
from backend.secuscan.models import SandboxConfig


# resolve_sandbox_config


def test_resolve_sandbox_config_returns_global_defaults():
    """Without a plugin override, returns base config from global settings."""
    config = resolve_sandbox_config(plugin_sandbox=None)
    assert isinstance(config, SandboxConfig)
    assert config.timeout_seconds > 0
    assert config.max_memory_mb > 0


def test_resolve_sandbox_config_applies_override_timeout():
    """Plugin override for timeout_seconds is applied."""
    override = SandboxConfig(timeout_seconds=999)
    config = resolve_sandbox_config(plugin_sandbox=override)
    assert config.timeout_seconds == 999


def test_resolve_sandbox_config_applies_override_memory():
    """Plugin override for max_memory_mb is applied."""
    override = SandboxConfig(max_memory_mb=2048)
    config = resolve_sandbox_config(plugin_sandbox=override)
    assert config.max_memory_mb == 2048


def test_resolve_sandbox_config_applies_override_network():
    """Plugin override for allow_network is applied."""
    override = SandboxConfig(allow_network=False)
    config = resolve_sandbox_config(plugin_sandbox=override)
    assert config.allow_network is False


def test_resolve_sandbox_config_partial_override():
    """Only specified override fields change; others retain global defaults."""
    override = SandboxConfig(max_output_bytes=1_000_000)
    config = resolve_sandbox_config(plugin_sandbox=override)
    assert config.max_output_bytes == 1_000_000
    assert config.timeout_seconds > 0
    assert config.max_memory_mb > 0


# classify_memory_violation


def test_classify_memory_violation_sigsegv_negative_11():
    assert classify_memory_violation(-11, "", 0, 100_000_000) is True


def test_classify_memory_violation_sigsegv_139():
    assert classify_memory_violation(139, "", 0, 100_000_000) is True


def test_classify_memory_violation_memeror_in_stderr():
    assert classify_memory_violation(1, "Python: MemoryError: out of memory", 0, 100_000_000) is True


def test_classify_memory_violation_cannot_allocate():
    assert classify_memory_violation(1, "fatal: Cannot allocate memory", 0, 100_000_000) is True


def test_classify_memory_violation_rss_near_limit():
    limit = 100_000_000
    rss = 96_000_000
    assert classify_memory_violation(1, "", rss, limit) is True


def test_classify_memory_violation_rss_below_95_percent():
    limit = 100_000_000
    rss = 90_000_000
    assert classify_memory_violation(1, "", rss, limit) is False


def test_classify_memory_violation_rss_at_limit_zero_exit():
    limit = 100_000_000
    rss = limit
    assert classify_memory_violation(0, "", rss, limit) is False


def test_classify_memory_violation_normal_exit():
    assert classify_memory_violation(0, "", 10_000_000, 100_000_000) is False


def test_classify_memory_violation_error_exit_no_indicators():
    assert classify_memory_violation(2, "some other error", 5_000_000, 100_000_000) is False


# _build_preexec_fn


def test_build_preexec_fn_returns_callable():
    config = SandboxConfig(max_memory_mb=256)
    result = _build_preexec_fn(config)
    assert callable(result)


@pytest.mark.skipif(platform.system() != "Linux", reason="RLIMIT_AS is Linux-only")
def test_build_preexec_fn_computes_correct_rlimit_bytes():
    # Verify the configured limit is converted to bytes correctly without
    # actually mutating the live process RLIMIT_AS. The 512 MB config must
    # produce a 536870912-byte limit.
    config = SandboxConfig(max_memory_mb=512)
    preexec = _build_preexec_fn(config)

    captured = {}

    fake_resource = type("R", (), {})()
    def _capture(limit_name, value):
        captured["limit_name"] = limit_name
        captured["value"] = value

    fake_resource.RLIMIT_AS = 9  # constant from the real resource module
    fake_resource.setrlimit = _capture

    with patch.dict("sys.modules", {"resource": fake_resource}):
        preexec()

    assert captured["limit_name"] == 9
    assert captured["value"] == (512 * 1024 * 1024, 512 * 1024 * 1024)


@pytest.mark.skipif(platform.system() != "Linux", reason="RLIMIT_AS is Linux-only")
def test_build_preexec_fn_does_not_mutate_live_process_limits():
    # Guard against the old test that called preexec() directly and changed
    # RLIMIT_AS for the whole pytest process. Here we patch the resource
    # module that preexec_fn imports inside the closure, so the live process
    # is never touched.
    import resource

    config = SandboxConfig(max_memory_mb=256)
    preexec = _build_preexec_fn(config)
    before = resource.getrlimit(resource.RLIMIT_AS)

    calls = []

    def _fake_setrlimit(name, value):
        calls.append((name, value))

    fake_resource = type("R", (), {})()
    fake_resource.RLIMIT_AS = resource.RLIMIT_AS
    fake_resource.setrlimit = _fake_setrlimit

    with patch.dict("sys.modules", {"resource": fake_resource}):
        preexec()

    after = resource.getrlimit(resource.RLIMIT_AS)
    assert before == after
    assert calls  # The preexec_fn still tried to set a limit, but on a fake module
