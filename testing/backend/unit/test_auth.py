"""
Tests for backend.secuscan.auth init_api_key function.

Covers:
- First call: generates a new key file with correct permissions
- Second call: loads the existing key file and returns the same key
- SECUSCAN_API_KEY_FILE env var overrides default path
- Key file contains expected 64-character hex string (secrets.token_hex(32))
- Two init_api_key calls with same data_dir return identical keys
- Invalid path: function creates parent directories
"""

import os
import stat

import pytest


class TestInitApiKey:
    def test_first_call_generates_new_key_file(self, tmp_path):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        try:
            key = auth_module.init_api_key(str(tmp_path))
            key_file = tmp_path / ".api_key"
            assert key_file.exists(), "Key file should be created"
            assert key_file.read_text().strip() == key
        finally:
            auth_module._api_key = original_key

    def test_second_call_loads_existing_key(self, tmp_path):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        try:
            key1 = auth_module.init_api_key(str(tmp_path))
            key2 = auth_module.init_api_key(str(tmp_path))
            assert key1 == key2, "Second call should return the same key"
        finally:
            auth_module._api_key = original_key

    def test_key_file_has_correct_permissions(self, tmp_path):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        try:
            key = auth_module.init_api_key(str(tmp_path))
            key_file = tmp_path / ".api_key"
            mode = key_file.stat().st_mode
            # Expect 0o600 (owner read/write only)
            assert stat.S_IMODE(mode) == 0o600, f"Expected 0o600, got {oct(stat.S_IMODE(mode))}"
        finally:
            auth_module._api_key = original_key

    def test_key_is_64_character_hex_string(self, tmp_path):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        try:
            key = auth_module.init_api_key(str(tmp_path))
            assert len(key) == 64, f"Expected 64 chars, got {len(key)}"
            int(key, 16)  # Should not raise if valid hex
        finally:
            auth_module._api_key = original_key

    def test_env_var_overrides_default_path(self, tmp_path, monkeypatch):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        custom_path = tmp_path / "custom_dir" / ".api_key"
        monkeypatch.setenv("SECUSCAN_API_KEY_FILE", str(custom_path))
        try:
            key = auth_module.init_api_key(str(tmp_path / "ignored"))
            assert custom_path.exists(), "Custom path should be used"
            assert custom_path.read_text().strip() == key
        finally:
            auth_module._api_key = original_key
            monkeypatch.delenv("SECUSCAN_API_KEY_FILE", raising=False)

    def test_creates_parent_directories(self, tmp_path):
        import backend.secuscan.auth_helpers as auth_module

        original_key = auth_module._api_key
        nested = tmp_path / "a" / "b" / "c"
        try:
            key = auth_module.init_api_key(str(nested))
            assert (nested / ".api_key").exists()
        finally:
            auth_module._api_key = original_key
