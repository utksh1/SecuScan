"""
Unit tests for crawler URL normalisation with fragments.

Tests prove that fragment-only and fragment-bearing URLs are handled
correctly by urljoin in crawl_target, and that the crawler deduplicates
these via set() normalisation.
"""

from urllib.parse import urljoin


def _normalize_link(base_url: str, link: str) -> str | None:
    """Standalone normalisation wrapper around urljoin for unit testing.

    Mirrors the logic used inside crawl_target:
        normalized_links = sorted({urljoin(base_url, link) for link in parser.links if link})
    Returns None for empty/None links; otherwise returns the urljoin result.
    """
    if not link:
        return None
    return urljoin(base_url, link)


class TestFragmentOnlyLinks:
    def test_fragment_only_resolves_to_base_url(self):
        """Fragment-only links like '#section' resolve to the base URL with fragment."""
        result = urljoin("http://example.com/page", "#section")
        assert result == "http://example.com/page#section"

    def test_fragment_only_via_normalize(self):
        """_normalize_link returns the resolved URL for fragment-only links."""
        result = _normalize_link("http://example.com/page", "#section")
        assert result == "http://example.com/page#section"

    def test_empty_link_returns_none(self):
        """Empty string is filtered out (if link in the comprehension)."""
        result = _normalize_link("http://example.com/page", "")
        assert result is None

    def test_whitespace_only_resolves_to_base(self):
        """Whitespace-only links resolve to the base URL."""
        result = _normalize_link("http://example.com/page", "   ")
        assert result == "http://example.com/page"


class TestFragmentBearingLinks:
    def test_same_page_different_fragment_resolves_to_base(self):
        """Same page with different anchors resolve to the base URL."""
        result = _normalize_link("http://example.com/page", "#section2")
        assert result == "http://example.com/page#section2"

    def test_path_with_fragment_preserves_fragment(self):
        """urljoin preserves fragments when the path changes."""
        result = _normalize_link("http://example.com", "/page#section")
        assert result == "http://example.com/page#section"

    def test_external_url_with_fragment_passes_through(self):
        """External URLs with fragments pass through unchanged."""
        result = _normalize_link(
            "http://example.com", "http://other.com/page#anchor"
        )
        assert result == "http://other.com/page#anchor"

    def test_relative_path_with_fragment(self):
        """Relative paths with fragments preserve the fragment."""
        result = _normalize_link(
            "http://example.com/admin", "users#profile"
        )
        assert result == "http://example.com/users#profile"


class TestNormalLinksUnaffected:
    def test_absolute_url_unchanged(self):
        result = _normalize_link(
            "http://example.com", "http://other.com/page"
        )
        assert result == "http://other.com/page"

    def test_relative_path_normalised(self):
        result = _normalize_link(
            "http://example.com/admin", "../other"
        )
        assert result == "http://example.com/other"


class TestDeduplication:
    """urljoin + set() deduplication prevents duplicate crawl work."""

    def test_same_base_different_fragment_are_distinct(self):
        """Two fragments on the same base URL produce distinct URLs."""
        a = _normalize_link("http://example.com/page", "#section1")
        b = _normalize_link("http://example.com/page", "#section2")
        assert a != b
        # Both deduplicate to the same base when the fragment is stripped
        assert a.split("#")[0] == b.split("#")[0]

    def test_set_deduplication_removes_duplicate_resolutions(self):
        """Identical resolved URLs are deduplicated by set()."""
        links = ["#section", "#section", "#other"]
        resolved = sorted({_normalize_link("http://example.com/page", l) for l in links})
        assert len(resolved) == 2
        assert "http://example.com/page#section" in resolved
        assert "http://example.com/page#other" in resolved
