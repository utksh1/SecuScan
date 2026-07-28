"""Unit tests for _sanitize_stderr in backend/secuscan/parser_sandbox.py."""

from backend.secuscan.parser_sandbox import _sanitize_stderr


class TestSanitizeStderr:
    def test_unix_paths_replaced(self):
        stderr = "Error in /home/user/project/main.py"
        result = _sanitize_stderr(stderr)
        assert "/home/user/project/main.py" not in result
        assert "[PATH]" in result

    def test_windows_paths_replaced(self):
        stderr = "Error in C:\\Users\\admin\\app.py"
        result = _sanitize_stderr(stderr)
        assert "C:\\Users\\admin\\app.py" not in result
        assert "[PATH]" in result

    def test_windows_forward_slash_paths_replaced(self):
        stderr = "Error in C:/Users/admin/app.py"
        result = _sanitize_stderr(stderr)
        assert "C:/Users/admin/app.py" not in result
        assert "[PATH]" in result

    def test_line_numbers_replaced(self):
        stderr = "ValueError at line 42"
        result = _sanitize_stderr(stderr)
        assert "line 42" not in result
        assert "[LINE]" in result

    def test_line_numbers_case_insensitive(self):
        stderr = "Error at LINE 10 and Line 20"
        result = _sanitize_stderr(stderr)
        assert "line 10" not in result.lower()
        assert "line 20" not in result.lower()

    def test_multiple_replacements(self):
        stderr = "Error in /home/user/file.py at line 5"
        result = _sanitize_stderr(stderr)
        assert "/home/user/file.py" not in result
        assert "line 5" not in result
        assert "[PATH]" in result
        assert "[LINE]" in result

    def test_no_sensitive_content_passed_through(self):
        stderr = "Something went wrong"
        result = _sanitize_stderr(stderr)
        assert result == stderr

    def test_truncation_default_500(self):
        long_stderr = "x" * 1000
        result = _sanitize_stderr(long_stderr)
        assert len(result) == 500

    def test_truncation_custom_max_chars(self):
        long_stderr = "x" * 200
        result = _sanitize_stderr(long_stderr, max_chars=100)
        assert len(result) == 100

    def test_truncation_preserves_replacements(self):
        # Both replacements must fit within max_chars=100 after truncation
        # /home/user/file.py (19) -> [PATH] (6): saves 13
        # line 42  (8) -> [LINE] (6): saves 2
        # Total saved: 15. Need original > 115 to trigger truncation at 100.
        long_stderr = "/home/user/file.py error at line 42  " + ("x" * 100)
        result = _sanitize_stderr(long_stderr, max_chars=100)
        assert "[PATH]" in result
        assert "[LINE]" in result
        assert len(result) == 100

    def test_empty_string(self):
        result = _sanitize_stderr("")
        assert result == ""

    def test_short_string_unchanged(self):
        stderr = "Short error"
        result = _sanitize_stderr(stderr)
        assert result == "Short error"

    def test_path_pattern_with_spaces(self):
        stderr = "Error in /var/log/ syslog"
        result = _sanitize_stderr(stderr)
        assert "[PATH]" in result

    def test_multiple_paths_replaced(self):
        stderr = "/first/path and /second/path"
        result = _sanitize_stderr(stderr)
        assert "/first/path" not in result
        assert "/second/path" not in result
        assert result.count("[PATH]") == 2
