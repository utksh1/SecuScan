"""
Unit tests for backend/secuscan/crawler _SurfaceParser HTML parsing.

Covers the _SurfaceParser HTMLParser subclass in isolation:
  - link extraction from <a href>
  - script extraction from <script src>
  - meta generator extraction from <meta name="generator">
  - form attribute parsing (action/method/id/name)
  - input extraction for text/password/hidden/file types
  - textarea and select treated as inputs
  - nested form state (no inputs after form closes)
"""

from __future__ import annotations

from backend.secuscan.crawler import _SurfaceParser


def _parse(html: str) -> _SurfaceParser:
    parser = _SurfaceParser()
    parser.feed(html)
    return parser


# ---------------------------------------------------------------------------
# links
# ---------------------------------------------------------------------------

def test_anchor_href_extracted():
    parser = _parse('<a href="https://example.com/page">Link</a>')
    assert "https://example.com/page" in parser.links


def test_multiple_anchor_links():
    parser = _parse(
        '<a href="/path1">One</a><a href="/path2">Two</a><a>No href</a>'
    )
    assert parser.links == ["/path1", "/path2"]


def test_links_case_insensitive_tag():
    parser = _parse('<A HREF="/path">Uppercase tag</A>')
    assert "/path" in parser.links


def test_script_src_extracted():
    parser = _parse('<script src="/static/app.js"></script>')
    assert "/static/app.js" in parser.scripts


def test_multiple_script_srcs():
    parser = _parse(
        '<script src="/a.js"></script><script src="/b.js"></script>'
    )
    assert parser.scripts == ["/a.js", "/b.js"]


def test_script_without_src_not_in_scripts():
    parser = _parse('<script>console.log(1)</script>')
    assert parser.scripts == []


# ---------------------------------------------------------------------------
# meta generators
# ---------------------------------------------------------------------------

def test_meta_generator_content_extracted():
    parser = _parse('<meta name="generator" content="WordPress 6.4">')
    assert "WordPress 6.4" in parser.meta_generators


def test_meta_generator_case_insensitive():
    parser = _parse('<META NAME="generator" CONTENT="Drupal 9">')
    assert "Drupal 9" in parser.meta_generators


def test_meta_generator_missing_content_not_added():
    parser = _parse('<meta name="generator">')
    assert parser.meta_generators == []


def test_non_generator_meta_not_added():
    parser = _parse('<meta name="description" content="A page">')
    assert parser.meta_generators == []


# ---------------------------------------------------------------------------
# forms
# ---------------------------------------------------------------------------

def test_form_action_extracted():
    parser = _parse('<form action="/submit"></form>')
    assert len(parser.forms) == 1
    assert parser.forms[0]["action"] == "/submit"


def test_form_method_default_is_get():
    parser = _parse('<form action="/search"></form>')
    assert parser.forms[0]["method"] == "get"


def test_form_method_preserved():
    parser = _parse('<form action="/login" method="POST"></form>')
    assert parser.forms[0]["method"] == "post"


def test_form_id_extracted():
    parser = _parse('<form id="login-form" action="/x"></form>')
    assert parser.forms[0]["id"] == "login-form"


def test_form_name_extracted():
    parser = _parse('<form name="search" action="/x"></form>')
    assert parser.forms[0]["name"] == "search"


def test_multiple_forms():
    parser = _parse(
        '<form action="/a"></form><form action="/b"></form>'
    )
    assert len(parser.forms) == 2
    assert parser.forms[0]["action"] == "/a"
    assert parser.forms[1]["action"] == "/b"


# ---------------------------------------------------------------------------
# inputs inside forms
# ---------------------------------------------------------------------------

def test_text_input_extracted():
    parser = _parse(
        '<form action="/x"><input type="text" name="q"></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert len(inputs) == 1
    assert inputs[0] == {"name": "q", "type": "text", "value": ""}


def test_password_input_extracted():
    parser = _parse(
        '<form action="/x"><input type="password" name="pwd" value="secret"></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert inputs[0] == {"name": "pwd", "type": "password", "value": "secret"}


def test_hidden_input_extracted():
    parser = _parse(
        '<form action="/x"><input type="hidden" name="csrf" value="tok123"></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert inputs[0] == {"name": "csrf", "type": "hidden", "value": "tok123"}


def test_file_input_extracted():
    parser = _parse(
        '<form action="/x" method="POST" enctype="multipart/form-data">'
        '<input type="file" name="upload"></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert inputs[0] == {"name": "upload", "type": "file", "value": ""}


def test_input_type_default_is_text():
    parser = _parse('<form action="/x"><input name="q"></form>')
    assert parser.forms[0]["inputs"][0]["type"] == "text"


def test_input_value_extracted():
    parser = _parse(
        '<form action="/x"><input type="text" name="q" value="search term"></form>'
    )
    assert parser.forms[0]["inputs"][0]["value"] == "search term"


def test_textarea_as_input():
    parser = _parse(
        '<form action="/x"><textarea name="bio">Hello</textarea></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert {"name": "bio", "type": "textarea", "value": ""} in inputs


def test_select_as_input():
    parser = _parse(
        '<form action="/x"><select name="country"></select></form>'
    )
    inputs = parser.forms[0]["inputs"]
    assert {"name": "country", "type": "select", "value": ""} in inputs


def test_inputs_after_form_close_not_included():
    parser = _parse(
        '<form action="/a"></form>'
        '<form action="/b"><input name="x"></form>'
    )
    # First form has no inputs; second form has the input
    assert parser.forms[0]["inputs"] == []
    assert parser.forms[1]["inputs"][0]["name"] == "x"


def test_input_outside_form_not_in_any_form():
    parser = _parse(
        '<form action="/x"></form>'
        '<input name="orphan">'
    )
    # The orphan input is not captured by any form
    assert parser.forms[0]["inputs"] == []


# ---------------------------------------------------------------------------
# case insensitivity
# ---------------------------------------------------------------------------

def test_tag_names_case_insensitive():
    parser = _parse('<FORM ACTION="/x"><INPUT NAME="q" TYPE="TEXT"></FORM>')
    assert parser.forms[0]["action"] == "/x"
    assert parser.forms[0]["inputs"][0]["name"] == "q"


def test_boolean_attributes_empty_string():
    parser = _parse('<form action="/x" novalue></form>')
    assert parser.forms[0]["action"] == "/x"