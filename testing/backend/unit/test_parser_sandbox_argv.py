from backend.secuscan import parser_sandbox
from backend.secuscan.parser_sandbox import _sandbox_argv


def test_returns_unshare_prefixed_argv_when_unshare_net_supported(monkeypatch):
    monkeypatch.setattr(parser_sandbox, "_unshare_net_supported", lambda: True)

    result = _sandbox_argv("/usr/bin/python3", "print('hello')")

    assert result == [
        "unshare",
        "--user",
        "--net",
        "--",
        "/usr/bin/python3",
        "-c",
        "print('hello')",
    ]


def test_returns_argv_without_unshare_when_unshare_net_not_supported(monkeypatch):
    monkeypatch.setattr(parser_sandbox, "_unshare_net_supported", lambda: False)

    result = _sandbox_argv("/usr/bin/python3", "print('hello')")

    assert result == ["/usr/bin/python3", "-c", "print('hello')"]
    assert "unshare" not in result


def test_with_different_python_executables(monkeypatch):
    monkeypatch.setattr(parser_sandbox, "_unshare_net_supported", lambda: True)

    result_a = _sandbox_argv("/usr/bin/python3.11", "code")
    result_b = _sandbox_argv("C:\\Python314\\python.exe", "code")

    assert result_a[4] == "/usr/bin/python3.11"
    assert result_b[4] == "C:\\Python314\\python.exe"


def test_with_different_bootstrap_code(monkeypatch):
    monkeypatch.setattr(parser_sandbox, "_unshare_net_supported", lambda: False)

    result_a = _sandbox_argv("python3", "import sys; sys.exit(0)")
    result_b = _sandbox_argv("python3", "")

    assert result_a == ["python3", "-c", "import sys; sys.exit(0)"]
    assert result_b == ["python3", "-c", ""]