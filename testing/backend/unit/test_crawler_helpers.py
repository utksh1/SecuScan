"""
Unit tests for crawler.py _SurfaceParser and _build_headers helpers.
"""

from __future__ import annotations

from backend.secuscan.crawler_helpers import _SurfaceParser, _build_headers


# _build_headers tests


def test_build_headers_default_user_agent():
    """Default headers include a User-Agent."""
    headers = _build_headers()
    assert "User-Agent" in headers
    assert headers["User-Agent"] == "SecuScan-Crawler/1.0"


def test_build_headers_default_accept():
    """Default headers include Accept."""
    headers = _build_headers()
    assert "Accept" in headers
    assert "text/html" in headers["Accept"]


def test_build_headers_extra_headers_added():
    """extra_headers are merged into the result."""
    headers = _build_headers({"X-Custom": "value123"})
    assert headers["X-Custom"] == "value123"
    assert headers["User-Agent"] == "SecuScan-Crawler/1.0"


def test_build_headers_extra_headers_none_values_skipped():
    """None values in extra_headers are not included."""
    headers = _build_headers({"X-Optional": None, "X-Real": "present"})
    assert "X-Optional" not in headers
    assert headers["X-Real"] == "present"


def test_build_headers_extra_headers_empty_key_skipped():
    """Empty-string keys in extra_headers are not included."""
    headers = _build_headers({"": "empty-key-value"})
    assert "" not in headers


# _SurfaceParser tests


def test_parser_extracts_links():
    """Links with href are collected."""
    parser = _SurfaceParser()
    parser.feed('<a href="/page1">Page 1</a><a href="/page2">Page 2</a>')
    assert parser.links == ["/page1", "/page2"]


def test_parser_extracts_scripts():
    """Script src attributes are collected."""
    parser = _SurfaceParser()
    parser.feed('<script src="/static/app.js"></script><script src="/lib.js"></script>')
    assert parser.scripts == ["/static/app.js", "/lib.js"]


def test_parser_extracts_meta_generators():
    """Meta generator tags are collected."""
    parser = _SurfaceParser()
    parser.feed('<meta name="generator" content="WordPress 6.0">')
    assert parser.meta_generators == ["WordPress 6.0"]


def test_parser_ignores_meta_without_generator():
    """Meta tags without name=generator are ignored."""
    parser = _SurfaceParser()
    parser.feed('<meta name="viewport" content="width=device-width">')
    assert parser.meta_generators == []


def test_parser_extracts_forms_basic():
    """Form tags are captured with action and method."""
    parser = _SurfaceParser()
    parser.feed('<form action="/submit" method="post"><input name="q"></form>')
    assert len(parser.forms) == 1
    assert parser.forms[0]["action"] == "/submit"
    assert parser.forms[0]["method"] == "post"
    assert parser.forms[0]["id"] == ""
    assert parser.forms[0]["name"] == ""


def test_parser_extracts_form_id_and_name():
    """Form id and name attributes are captured."""
    parser = _SurfaceParser()
    parser.feed('<form id="search-form" name="searchForm" action="/search">')
    assert parser.forms[0]["id"] == "search-form"
    assert parser.forms[0]["name"] == "searchForm"


def test_parser_extracts_form_inputs():
    """Input fields inside forms are collected."""
    parser = _SurfaceParser()
    parser.feed(
        '<form><input name="username" type="text"><input name="token" type="hidden" value="abc123"></form>'
    )
    assert len(parser.forms[0]["inputs"]) == 2
    assert parser.forms[0]["inputs"][0]["name"] == "username"
    assert parser.forms[0]["inputs"][0]["type"] == "text"
    assert parser.forms[0]["inputs"][1]["name"] == "token"
    assert parser.forms[0]["inputs"][1]["type"] == "hidden"
    assert parser.forms[0]["inputs"][1]["value"] == "abc123"


def test_parser_extracts_textarea():
    """Textarea tags are captured as inputs."""
    parser = _SurfaceParser()
    parser.feed('<form><textarea name="comment"></textarea></form>')
    assert any(i["name"] == "comment" and i["type"] == "textarea" for i in parser.forms[0]["inputs"])


def test_parser_extracts_select():
    """Select tags are captured as inputs."""
    parser = _SurfaceParser()
    parser.feed('<form><select name="country"><option>US</option></select></form>')
    assert any(i["name"] == "country" and i["type"] == "select" for i in parser.forms[0]["inputs"])


def test_parser_nested_forms_both_recorded():
    """Nested forms: both outer and inner are recorded."""
    parser = _SurfaceParser()
    parser.feed('<form id="outer"><form id="inner"></form></form>')
    assert len(parser.forms) == 2
    assert parser.forms[0]["id"] == "outer"
    assert parser.forms[1]["id"] == "inner"


def test_parser_default_form_method():
    """Forms without method default to GET."""
    parser = _SurfaceParser()
    parser.feed('<form action="/search"></form>')
    assert parser.forms[0]["method"] == "get"


def test_parser_empty_html():
    """Empty HTML produces no links, forms, scripts, or meta generators."""
    parser = _SurfaceParser()
    parser.feed("")
    assert parser.links == []
    assert parser.forms == []
    assert parser.scripts == []
    assert parser.meta_generators == []
