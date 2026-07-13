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


def test_sanitised_env_drops_pythonpath():
    """PYTHONPATH is dropped: an inherited value is an import-injection vector."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"PYTHONPATH": "/opt/attacker"}, clear=False):
        result = _sanitised_env()
    assert "PYTHONPATH" not in result


def test_sanitised_env_drops_home():
    """HOME is dropped: it controls the ~/.local user-site sys.path entry."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    with patch.dict("os.environ", {"HOME": "/attacker/home"}, clear=False):
        result = _sanitised_env()
    assert "HOME" not in result


def test_sanitised_env_disables_user_site():
    """PYTHONNOUSERSITE is forced on so ~/.local site-packages is ignored."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    result = _sanitised_env()
    assert result.get("PYTHONNOUSERSITE") == "1"


def test_sanitised_env_sets_safe_path():
    """PYTHONSAFEPATH is forced on so CWD/'' is not prepended to sys.path."""
    from backend.secuscan.parser_sandbox import _sanitised_env
    result = _sanitised_env()
    assert result.get("PYTHONSAFEPATH") == "1"


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


# ---------------------------------------------------------------------------
# _privilege_drop_kwargs()
# ---------------------------------------------------------------------------


def test_privilege_drop_noop_when_not_root():
    """When the backend is not root there is nothing to drop; kwargs are empty."""
    from backend.secuscan import parser_sandbox
    with patch.object(parser_sandbox.os, "geteuid", return_value=1000, create=True):
        assert parser_sandbox._privilege_drop_kwargs() == {}


def test_privilege_drop_noop_on_non_posix():
    """On a platform without posix semantics the drop is a no-op."""
    from backend.secuscan import parser_sandbox
    with patch.object(parser_sandbox.os, "name", "nt"):
        assert parser_sandbox._privilege_drop_kwargs() == {}


def test_privilege_drop_targets_nobody_when_root():
    """As root, the child is dropped to the resolved unprivileged account."""
    import sys
    import types
    from backend.secuscan import parser_sandbox

    class _FakePw:
        pw_uid = 12345
        pw_gid = 23456

    # `pwd` is POSIX-only; inject a fake so this runs on any CI host.
    fake_pwd = types.SimpleNamespace(getpwnam=lambda name: _FakePw())
    with patch.object(parser_sandbox.os, "name", "posix"), \
            patch.object(parser_sandbox.os, "geteuid", return_value=0, create=True), \
            patch.dict(sys.modules, {"pwd": fake_pwd}):
        kwargs = parser_sandbox._privilege_drop_kwargs()

    assert kwargs["user"] == 12345
    assert kwargs["group"] == 23456
    assert kwargs["extra_groups"] == []


def test_privilege_drop_falls_back_to_65534_when_nobody_missing():
    """A host without a 'nobody' account still gets a safe unprivileged target."""
    import sys
    import types
    from backend.secuscan import parser_sandbox

    def _missing(name):
        raise KeyError(name)

    fake_pwd = types.SimpleNamespace(getpwnam=_missing)
    with patch.object(parser_sandbox.os, "name", "posix"), \
            patch.object(parser_sandbox.os, "geteuid", return_value=0, create=True), \
            patch.dict(sys.modules, {"pwd": fake_pwd}):
        kwargs = parser_sandbox._privilege_drop_kwargs()

    assert kwargs["user"] == parser_sandbox._NOBODY_UID
    assert kwargs["group"] == parser_sandbox._NOBODY_GID
