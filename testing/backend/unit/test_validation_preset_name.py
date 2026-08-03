"""
Unit tests for validate_preset_name and _resolve_host_ips in validation.py.
"""

from unittest.mock import patch

from backend.secuscan.validation import validate_preset_name, _resolve_host_ips


class TestValidatePresetName:
    def test_none_preset_returns_true(self):
        """validate_preset_name returns (True, '') when preset is None."""
        ok, msg = validate_preset_name("nmap", None, None)
        assert ok is True
        assert msg == ""

    def test_empty_string_preset_returns_true(self):
        """validate_preset_name returns (True, '') when preset is empty string."""
        ok, msg = validate_preset_name("nmap", "", None)
        assert ok is True
        assert msg == ""

    def test_valid_preset_returns_true(self):
        """validate_preset_name returns (True, '') when preset is in available_presets."""
        ok, msg = validate_preset_name("nmap", "fast", {"fast": {}, "full": {}})
        assert ok is True
        assert msg == ""

    def test_unknown_preset_returns_false(self):
        """validate_preset_name returns (False, 'Unknown preset ...') when not found."""
        ok, msg = validate_preset_name("nmap", "nonexistent", {"fast": {}})
        assert ok is False
        assert "Unknown preset" in msg
        assert "nonexistent" in msg
        assert "nmap" in msg

    def test_unknown_preset_empty_presets_returns_false(self):
        """validate_preset_name returns (False, ...) when available_presets is empty dict."""
        ok, msg = validate_preset_name("nmap", "anything", {})
        assert ok is False
        assert "Unknown preset" in msg

    def test_unknown_preset_none_presets_returns_false(self):
        """validate_preset_name returns (False, ...) when available_presets is None."""
        ok, msg = validate_preset_name("nmap", "anything", None)
        assert ok is False
        assert "Unknown preset" in msg

    def test_plugin_id_appears_in_error_message(self):
        """The error message includes the plugin_id for context."""
        ok, msg = validate_preset_name("custom-scanner", "bad-preset", {})
        assert ok is False
        assert "custom-scanner" in msg


class TestResolveHostIpsDnsFailure:
    def test_returns_empty_list_on_oserror(self):
        """_resolve_host_ips returns [] when socket.getaddrinfo raises OSError."""
        with patch("socket.getaddrinfo", side_effect=OSError("Name resolution failed")):
            result = _resolve_host_ips("unresolvable.invalid")
            assert result == []

    def test_returns_empty_list_on_gaierror(self):
        """_resolve_host_ips returns [] when socket.getaddrinfo raises gaierror."""
        import socket as _socket
        with patch("socket.getaddrinfo", side_effect=_socket.gaierror("No address associated with name")):
            result = _resolve_host_ips("nonexistent.local")
            assert result == []
