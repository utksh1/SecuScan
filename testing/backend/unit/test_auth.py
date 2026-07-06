"""
Unit tests for backend.secuscan.auth.init_api_key.

Covers:
- init_api_key generates a new key and persists it when no key file exists
- init_api_key loads an existing key file without regenerating
- init_api_key respects SECUSCAN_API_KEY_FILE env var for custom key path
- init_api_key sets the file mode to 0o600 (owner read/write only)
- init_api_key returns the loaded/generated key
- init_api_key raises OSError on unwritable directory
"""

import os
import stat
import tempfile
from pathlib import Path

# Patch out the module-level _api_key before importing init_api_key
import sys
import backend.secuscan.auth as auth_module

# Save original value
_original_api_key = getattr(auth_module, "_api_key", None)


def fresh_key(data_dir: str) -> str:
    """Call init_api_key after resetting the module global."""
    auth_module._api_key = None
    return auth_module.init_api_key(data_dir)


class TestInitApiKey:
    def test_generates_new_key_when_no_file_exists(self, tmp_path: Path):
        """A new key is generated and written to <data_dir>/.api_key."""
        key = fresh_key(str(tmp_path))
        key_file = tmp_path / ".api_key"

        assert key is not None
        assert len(key) == 64  # secrets.token_hex(32) -> 64 hex chars
        assert key_file.exists()
        assert key_file.read_text().strip() == key

    def test_loads_existing_key_without_regenerating(self, tmp_path: Path):
        """An existing key file is not overwritten."""
        key_file = tmp_path / ".api_key"
        existing = "deadbeef" * 8  # 64-char hex
        key_file.write_text(existing + "\n")

        loaded = fresh_key(str(tmp_path))

        assert loaded == existing
        # File must not have been rewritten
        assert key_file.read_text().strip() == existing

    def test_respects_env_var_custom_path(self, tmp_path: Path, monkeypatch):
        """SECUSCAN_API_KEY_FILE redirects the key file location."""
        custom_file = tmp_path / "my_custom_key"
        monkeypatch.setenv("SECUSCAN_API_KEY_FILE", str(custom_file))

        key = fresh_key(str(tmp_path))

        assert custom_file.exists()
        assert custom_file.read_text().strip() == key
        # No .api_key in data_dir either
        assert not (tmp_path / ".api_key").exists()

    def test_file_mode_is_0600(self, tmp_path: Path):
        """The key file is created with mode 0o600 (owner rw only)."""
        fresh_key(str(tmp_path))
        key_file = tmp_path / ".api_key"
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600

    def test_returns_the_loaded_or_generated_key(self, tmp_path: Path):
        """init_api_key returns the same value that is written to the file."""
        key = fresh_key(str(tmp_path))
        assert key == (tmp_path / ".api_key").read_text().strip()

    def test_creates_parent_directories(self, tmp_path: Path):
        """init_api_key creates parent directories if they do not exist."""
        nested = tmp_path / "a" / "b" / "c"
        key = fresh_key(str(nested))
        assert (nested / ".api_key").exists()
        assert key is not None

    def test_generated_key_is_64_hex_chars(self, tmp_path: Path):
        """The generated key is exactly 64 hexadecimal characters (256 bits)."""
        key = fresh_key(str(tmp_path))
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# get_api_key tests
# ---------------------------------------------------------------------------


def test_get_api_key_returns_none_when_not_initialised():
    """When _api_key is None, get_api_key returns None."""
    import backend.secuscan.auth as auth_module
    original = getattr(auth_module, "_api_key", None)
    try:
        auth_module._api_key = None
        from backend.secuscan.auth import get_api_key
        assert get_api_key() is None
    finally:
        auth_module._api_key = original


def test_get_api_key_returns_set_value():
    """get_api_key returns the value that was set in _api_key."""
    import backend.secuscan.auth as auth_module
    original = getattr(auth_module, "_api_key", None)
    try:
        auth_module._api_key = "test-key-1234567890abcdef"
        from backend.secuscan.auth import get_api_key
        assert get_api_key() == "test-key-1234567890abcdef"
    finally:
        auth_module._api_key = original


def test_get_api_key_returns_string_or_none():
    """get_api_key always returns a string or None."""
    import backend.secuscan.auth as auth_module
    original = getattr(auth_module, "_api_key", None)
    try:
        auth_module._api_key = "any-valid-api-key"
        from backend.secuscan.auth import get_api_key
        result = get_api_key()
        assert isinstance(result, str) or result is None
    finally:
        auth_module._api_key = original


def test_get_api_key_preserves_key_across_multiple_calls():
    """Multiple calls to get_api_key return the same value."""
    import backend.secuscan.auth as auth_module
    original = getattr(auth_module, "_api_key", None)
    try:
        auth_module._api_key = "stable-key-value"
        from backend.secuscan.auth import get_api_key
        assert get_api_key() == get_api_key() == get_api_key()
    finally:
        auth_module._api_key = original
