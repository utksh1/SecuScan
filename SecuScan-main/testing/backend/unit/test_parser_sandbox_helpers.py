"""
Unit tests for parser_sandbox pure helpers.

Covers _sanitised_env() from backend.secuscan.parser_sandbox.
"""

import pytest
from unittest.mock import patch


def test_sanitised_env_returns_dict():
    """_sanitised_env returns a dictionary."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    result = _sanitised_env()
    assert isinstance(result, dict)


def test_sanitised_env_keeps_path():
    """PATH is retained in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=False):
        result = _sanitised_env()
    assert "PATH" in result


def test_sanitised_env_keeps_pythonpath():
    """PYTHONPATH is retained in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"PYTHONPATH": "/opt/python"}, clear=False):
        result = _sanitised_env()
    assert "PYTHONPATH" in result


def test_sanitised_env_keeps_home():
    """HOME is retained in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"HOME": "/root"}, clear=False):
        result = _sanitised_env()
    assert "HOME" in result


def test_sanitised_env_strips_vault_key():
    """SECUSCAN_VAULT_KEY is not present in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {
        "SECUSCAN_VAULT_KEY": "secret123",
        "PATH": "/usr/bin",
    }, clear=False):
        result = _sanitised_env()
    assert "SECUSCAN_VAULT_KEY" not in result


def test_sanitised_env_strips_aws_secrets():
    """AWS_SECRET_ACCESS_KEY is not present in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "PATH": "/usr/bin",
    }, clear=False):
        result = _sanitised_env()
    assert "AWS_SECRET_ACCESS_KEY" not in result


def test_sanitised_env_strips_database_url():
    """DATABASE_URL is not present in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {
        "DATABASE_URL": "sqlite:///secuscan.db",
        "PATH": "/usr/bin",
    }, clear=False):
        result = _sanitised_env()
    assert "DATABASE_URL" not in result


def test_sanitised_env_preserves_path_value():
    """PATH value is preserved in the sanitised environment."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "SECUSCAN_VAULT_KEY": "secret",
    }, clear=False):
        result = _sanitised_env()
    assert result.get("PATH") == "/usr/local/bin:/usr/bin:/bin"


def test_sanitised_env_is_deterministic():
    """Calling _sanitised_env multiple times produces consistent results."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"PATH": "/usr/bin"}, clear=False):
        r1 = _sanitised_env()
        r2 = _sanitised_env()
    assert r1 == r2
