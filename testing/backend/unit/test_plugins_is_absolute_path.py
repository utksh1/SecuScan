"""Unit tests for _is_absolute_path in backend/secuscan/plugins.py."""

import pytest

from backend.secuscan.plugins_helpers import _is_absolute_path


class TestIsAbsolutePath:
    def test_unix_absolute_path_slash(self):
        assert _is_absolute_path("/") is True
        assert _is_absolute_path("/usr/bin") is True
        assert _is_absolute_path("/home/user/file.py") is True
        assert _is_absolute_path("/var/log/../../../etc/passwd") is True

    def test_unix_relative_path(self):
        assert _is_absolute_path("usr/bin") is False
        assert _is_absolute_path("./file.py") is False
        assert _is_absolute_path("../file.py") is False
        assert _is_absolute_path("file.py") is False

    def test_windows_drive_letter_backslash(self):
        assert _is_absolute_path("C:\\") is True
        assert _is_absolute_path("C:\\Windows\\System32") is True
        assert _is_absolute_path("D:\\Users\\file.txt") is True

    def test_windows_drive_letter_forward_slash(self):
        assert _is_absolute_path("C:/") is True
        assert _is_absolute_path("C:/Windows/System32") is True
        assert _is_absolute_path("D:/Users/file.txt") is True

    def test_windows_relative_path(self):
        assert _is_absolute_path("Windows\\System32") is False
        assert _is_absolute_path("Users\\file.txt") is False
        assert _is_absolute_path("file.txt") is False

    def test_unc_path(self):
        assert _is_absolute_path("\\\\server\\share") is True
        assert _is_absolute_path("\\\\server\\share\\folder\\file") is True

    def test_edge_cases(self):
        assert _is_absolute_path("") is False
        assert _is_absolute_path("a") is False
        assert _is_absolute_path("/") is True
        assert _is_absolute_path("~") is False
        assert _is_absolute_path("$HOME/file") is False
