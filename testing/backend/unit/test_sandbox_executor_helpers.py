"""
Unit tests for sandbox_executor.py helper functions.

Covers: resolve_sandbox_config, classify_memory_violation, _build_preexec_fn
"""

import platform
from backend.secuscan.sandbox_executor import (
    resolve_sandbox_config,
    classify_memory_violation,
    _build_preexec_fn,
)
from backend.secuscan.models import SandboxConfig


# ── resolve_sandbox_config ────────────────────────────────────────────────────


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
    # max_output_bytes overridden
    assert config.max_output_bytes == 1_000_000
    # timeout and memory still from global settings
    assert config.timeout_seconds > 0
    assert config.max_memory_mb > 0


# ── classify_memory_violation ─────────────────────────────────────────────────


def test_classify_memory_violation_sigsegv_negative_11():
    """SIGSEGV exit code -11 indicates memory violation."""
    assert classify_memory_violation(-11, "", 0, 100_000_000) is True


def test_classify_memory_violation_sigsegv_139():
    """Exit code 139 (128 + 11) also indicates SIGSEGV."""
    assert classify_memory_violation(139, "", 0, 100_000_000) is True


def test_classify_memory_violation_memeror_in_stderr():
    """'MemoryError' in stderr indicates OOM."""
    assert classify_memory_violation(1, "Python: MemoryError: out of memory", 0, 100_000_000) is True


def test_classify_memory_violation_cannot_allocate():
    """'Cannot allocate memory' in stderr indicates OOM."""
    assert classify_memory_violation(1, "fatal: Cannot allocate memory", 0, 100_000_000) is True


def test_classify_memory_violation_rss_near_limit():
    """RSS approaching 95% of limit with non-zero exit code is flagged."""
    limit = 100_000_000
    rss = 96_000_000  # 96% of limit
    assert classify_memory_violation(1, "", rss, limit) is True


def test_classify_memory_violation_rss_below_95_percent():
    """RSS below 95% of limit is not flagged as memory violation."""
    limit = 100_000_000
    rss = 90_000_000  # 90% of limit
    assert classify_memory_violation(1, "", rss, limit) is False


def test_classify_memory_violation_rss_at_limit_zero_exit():
    """RSS at limit but zero exit code is not flagged (clean exit)."""
    limit = 100_000_000
    rss = limit
    assert classify_memory_violation(0, "", rss, limit) is False


def test_classify_memory_violation_normal_exit():
    """Normal exit with no OOM indicators is not flagged."""
    assert classify_memory_violation(0, "", 10_000_000, 100_000_000) is False


def test_classify_memory_violation_error_exit_no_indicators():
    """Non-zero exit without memory-related indicators is not flagged."""
    assert classify_memory_violation(2, "some other error", 5_000_000, 100_000_000) is False


# ── _build_preexec_fn ─────────────────────────────────────────────────────────


def test_build_preexec_fn_returns_callable():
    """_build_preexec_fn returns a callable on Linux."""
    config = SandboxConfig(max_memory_mb=256)
    result = _build_preexec_fn(config)
    assert callable(result)


def test_build_preexec_fn_uses_correct_limit():
    """The returned callable sets RLIMIT_AS to configured memory limit on Linux."""
    import resource
    if platform.system() != "Linux":
        return  # RLIMIT_AS is Linux-only
    config = SandboxConfig(max_memory_mb=512)
    preexec = _build_preexec_fn(config)
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    preexec()
    new_soft, new_hard = resource.getrlimit(resource.RLIMIT_AS)
    assert new_soft == 512 * 1024 * 1024
    # Restore if possible; if hard was unlimited (-1) this may raise - ignore
    try:
        resource.setrlimit(resource.RLIMIT_AS, (soft if soft != -1 else new_hard, new_hard))
    except (ValueError, OSError):
        pass  # Container environments may restrict limit restoration
