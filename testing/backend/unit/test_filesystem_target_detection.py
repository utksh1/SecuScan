import pytest

from backend.secuscan.routes import is_filesystem_target


@pytest.mark.parametrize("target", [
    "/home/user/file.txt",
    "./local/file.txt",
    "../relative/path",
    "~/documents/file.txt",
    "C:\\Users\\Admin\\file.txt",
    "\\\\server\\share\\file.txt",
    ".\\local\\file.txt",
    "..\\relative\\path",
])
def test_is_filesystem_target_detects_valid_paths(target):
    assert is_filesystem_target(target) is True


@pytest.mark.parametrize("target", [
    "8.8.8.8/32",
    "192.168.1.0/24",
    "google.com/test",
    "example.com/api",
    "http://example.com/test",
    "https://example.com/api",
    "user@example.com/path",
])
def test_is_filesystem_target_rejects_non_filesystem_targets(target):
    assert is_filesystem_target(target) is False
