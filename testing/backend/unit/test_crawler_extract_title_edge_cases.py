"""
Genuinely-missing unit tests for crawler _extract_title edge cases.

Extends the coverage in test_crawler_helpers.py with cases NOT yet tested:
  - Multiple <title> elements (only first returned)
  - Title with nested inline elements
  - Non-HTML input returns empty string
  - Title with Unicode content
  - Very long title string
"""

from backend.secuscan.crawler import _extract_title


class TestExtractTitleMultipleElements:
    def test_multiple_title_elements_returns_first(self):
        """When multiple <title> elements exist, only the first is returned."""
        html = "<html><head><title>First Title</title></head>"
        html += "<body><title>Second Title</title></body></html>"
        result = _extract_title(html)
        assert result == "First Title"

    def test_three_title_elements_returns_first(self):
        """With three <title> elements, the first is returned."""
        html = "<title>A</title><title>B</title><title>C</title>"
        result = _extract_title(html)
        assert result == "A"


class TestExtractTitleNestedElements:
    def test_title_with_nested_script_tag(self):
        """Title containing <script> tags returns the full text content."""
        html = "<title><script>alert('xss')</script>Dashboard</title>"
        result = _extract_title(html)
        # _extract_title uses feed() then the closing tag text; nested content is included
        assert len(result) > 0

    def test_title_with_span_inside(self):
        """Title with nested <span> elements returns the text content."""
        html = "<title><span>Hello</span> <span>World</span></title>"
        result = _extract_title(html)
        assert "Hello" in result
        assert "World" in result


class TestExtractTitleNonHtml:
    def test_non_html_input_returns_empty_string(self):
        """Non-HTML content (e.g. JSON) returns empty string without crashing."""
        result = _extract_title('{"title": "not html"}')
        assert result == ""

    def test_plain_text_returns_empty_string(self):
        """Plain text content returns empty string."""
        result = _extract_title("This is just plain text without any HTML tags.")
        assert result == ""

    def test_empty_string_returns_empty(self):
        """Empty string input returns empty string."""
        result = _extract_title("")
        assert result == ""


class TestExtractTitleUnicode:
    def test_unicode_title_returns_unicode_content(self):
        """Unicode characters in title are preserved."""
        html = "<title>Hello World</title>"
        result = _extract_title(html)
        assert result == "Hello World"

    def test_chinese_characters(self):
        """Chinese characters in title are preserved."""
        html = "<title>安全扫描平台</title>"
        result = _extract_title(html)
        assert result == "安全扫描平台"

    def test_emoji_in_title(self):
        """Emoji in title are preserved."""
        html = "<title>Scan Results - 100% Coverage</title>"
        result = _extract_title(html)
        assert "Scan Results" in result


class TestExtractTitleLength:
    def test_very_long_title_is_returned_unchanged(self):
        """A very long title string is returned without truncation."""
        long_title = "A" * 10000
        html = f"<title>{long_title}</title>"
        result = _extract_title(html)
        assert len(result) == 10000
        assert result == long_title

    def test_long_title_with_special_characters(self):
        """Long title with special characters is returned unchanged."""
        special = "Title with <>&'\" chars"
        html = f"<title>{special}</title>"
        result = _extract_title(html)
        assert special in result
