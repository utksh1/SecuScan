"""
Genuinely-missing unit tests for crawler.py surface-parsing helpers.

The bulk of crawler helper coverage lives in testing/backend/unit/test_crawler_helpers.py
(merged via PR #979). This file only contains cases that are NOT already covered
there, to avoid duplicate broad helper coverage.

Currently covered here (and only here):
  - _extract_title on a malformed/unclosed <title> tag
  - _extract_tech_hints deduplicates identical values across multiple headers
  - _extract_cms_hints deduplicates identical CMS values from different sources
  - _classify_path_hint returns 'login' for the '/user/login' variant
  - _normalize_form with a non-standard method (DELETE) is state_changing
  - _normalize_form when inputs contain a non-dict entry is tolerated
"""

from backend.secuscan.crawler import (
    _classify_path_hint,
    _extract_cms_hints,
    _extract_tech_hints,
    _extract_title,
    _normalize_form,
)


# _extract_title — malformed input


def test_extract_title_unclosed_tag_returns_empty():
    # Opening <title> with no closing </title> — the function must not crash
    # and must return "" rather than matching some later "</title>" in the
    # document.
    assert _extract_title("<title>Never closed") == ""


# _extract_tech_hints — dedup across multiple header channels


def test_extract_tech_hints_dedupes_identical_values():
    # When the same value appears in both 'server' and 'x-powered-by'
    # headers, the hint list must contain it only once.
    headers = {"server": "Apache", "x-powered-by": "Apache"}
    result = _extract_tech_hints(headers, [], [], "")
    assert result.count("Apache") == 1


# _extract_cms_hints — dedup across channels


def test_extract_cms_hints_dedupes_across_channels():
    # 'wordpress' detected from both meta and body should appear once.
    result = _extract_cms_hints(["WordPress"], "wp-content here", [])
    assert result.count("wordpress") == 1


# _classify_path_hint — extra login path


def test_classify_path_hint_user_login():
    # The 'login' category uses /user/login as a token, which is not the same
    # as /login alone. Verify the token is matched.
    assert _classify_path_hint("https://example.com/user/login") == "login"


# _normalize_form — DELETE method and non-dict inputs entry


def test_normalize_form_delete_method_is_state_changing():
    form = {"method": "delete", "action": "/api/resource/1", "inputs": []}
    result = _normalize_form("https://example.com", form)
    assert result["state_changing"] is True


def test_normalize_form_tolerates_non_dict_input_item():
    # A non-dict item in the inputs list must not crash the function.
    form = {
        "method": "post",
        "action": "/submit",
        "inputs": ["not-a-dict", {"name": "user", "type": "text"}],
    }
    result = _normalize_form("https://example.com", form)
    # The valid dict is still counted; the bad entry is skipped without raising.
    assert result["input_count"] == 2
    assert result["state_changing"] is True
