from backend.secuscan.routes import _escape_like


def test_normal_string_passes_through_unchanged():
    assert _escape_like("hello world") == "hello world"
    assert _escape_like("example.com") == "example.com"


def test_backslash_is_escaped_to_double_backslash():
    assert _escape_like("\\") == "\\\\"
    assert _escape_like("C:\\path\\to\\file") == "C:\\\\path\\\\to\\\\file"


def test_percent_sign_is_escaped():
    assert _escape_like("%") == "\\%"
    assert _escape_like("100% done") == "100\\% done"


def test_underscore_is_escaped():
    assert _escape_like("_") == "\\_"
    assert _escape_like("my_variable") == "my\\_variable"


def test_multiple_wildcards_are_all_escaped():
    assert _escape_like("%%__") == "\\%\\%\\_\\_"
    assert _escape_like("a%b_c%d_e") == "a\\%b\\_c\\%d\\_e"


def test_empty_string_returns_empty_string():
    assert _escape_like("") == ""


def test_mixed_content_with_all_wildcard_types():
    # Backslash must be escaped first so it doesn't double-escape the
    # backslashes introduced when escaping % and _.
    assert _escape_like("100%_off\\sale") == "100\\%\\_off\\\\sale"
    assert _escape_like("a\\b%c_d") == "a\\\\b\\%c\\_d"