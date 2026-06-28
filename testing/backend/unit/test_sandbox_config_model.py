"""
Unit tests for SandboxConfig in backend/secuscan/models.py.

Verifies sandbox execution configuration: field defaults and override behavior.
"""

from backend.secuscan.models import SandboxConfig


class TestSandboxConfigDefaults:
    def test_no_args_creates_valid_instance(self):
        """SandboxConfig with no arguments creates a valid instance."""
        config = SandboxConfig()
        assert config is not None
        assert isinstance(config.timeout_seconds, int)

    def test_timeout_seconds_has_default(self):
        """timeout_seconds defaults to 120 seconds."""
        config = SandboxConfig()
        assert config.timeout_seconds == 120

    def test_max_memory_mb_has_default(self):
        """max_memory_mb defaults to 512 MB."""
        config = SandboxConfig()
        assert config.max_memory_mb == 512

    def test_max_output_bytes_has_default(self):
        """max_output_bytes defaults to 5_242_880 bytes (5 MB)."""
        config = SandboxConfig()
        assert config.max_output_bytes == 5_242_880

    def test_allow_network_defaults_to_true(self):
        """allow_network defaults to True (network allowed by default)."""
        config = SandboxConfig()
        assert config.allow_network is True


class TestSandboxConfigOverrides:
    def test_timeout_override_applied(self):
        """Explicit timeout_seconds override is accepted."""
        config = SandboxConfig(timeout_seconds=300)
        assert config.timeout_seconds == 300

    def test_memory_override_applied(self):
        """Explicit max_memory_mb override is accepted."""
        config = SandboxConfig(max_memory_mb=2048)
        assert config.max_memory_mb == 2048

    def test_output_bytes_override_applied(self):
        """Explicit max_output_bytes override is accepted."""
        config = SandboxConfig(max_output_bytes=10_485_760)
        assert config.max_output_bytes == 10_485_760

    def test_network_disallowed_override_applied(self):
        """Explicit allow_network=False override is accepted."""
        config = SandboxConfig(allow_network=False)
        assert config.allow_network is False

    def test_multiple_overrides_applied(self):
        """Multiple overrides can be applied simultaneously."""
        config = SandboxConfig(
            timeout_seconds=60,
            max_memory_mb=256,
            allow_network=False,
        )
        assert config.timeout_seconds == 60
        assert config.max_memory_mb == 256
        assert config.allow_network is False

    def test_fields_are_accessible(self):
        """All four fields are accessible on the model."""
        config = SandboxConfig()
        assert hasattr(config, "timeout_seconds")
        assert hasattr(config, "max_memory_mb")
        assert hasattr(config, "max_output_bytes")
        assert hasattr(config, "allow_network")

    def test_repr_includes_all_fields(self):
        """repr of the model includes the configured values."""
        config = SandboxConfig(timeout_seconds=45, max_memory_mb=128)
        repr_str = repr(config)
        assert "45" in repr_str
        assert "128" in repr_str
