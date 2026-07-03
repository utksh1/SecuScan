"""
Unit tests for backend.secuscan.executor_target_helpers.extract_target.

The helper was extracted from executor.py into a small import-safe module so
that it can be unit-tested without pulling in the heavy FastAPI/cache chain.
executor.py re-exports it so existing call sites keep working unchanged.
"""

from backend.secuscan.executor_target_helpers import extract_target


class TestExtractTarget:
    def test_target_key_returns_target_value(self):
        """When 'target' is present, its value is returned."""
        inputs = {"target": "https://example.com", "url": "https://other.com"}
        assert extract_target(inputs) == "https://example.com"

    def test_url_without_target_returns_url(self):
        """When 'url' is present but not 'target', url is returned."""
        inputs = {"url": "https://example.com", "host": "example.com"}
        assert extract_target(inputs) == "https://example.com"

    def test_host_without_target_or_url_returns_host(self):
        """When 'host' is present but not 'target' or 'url', host is returned."""
        inputs = {"host": "example.com", "domain": "example.org"}
        assert extract_target(inputs) == "example.com"

    def test_domain_without_prior_keys_returns_domain(self):
        """When 'domain' is the first available key, its value is returned."""
        inputs = {"domain": "example.com"}
        assert extract_target(inputs) == "example.com"

    def test_priority_order_target_url_host_domain(self):
        """Keys are checked in priority order: target > url > host > domain."""
        inputs = {
            "target": "from-target",
            "url": "from-url",
            "host": "from-host",
            "domain": "from-domain",
        }
        assert extract_target(inputs) == "from-target"

        del inputs["target"]
        assert extract_target(inputs) == "from-url"

        del inputs["url"]
        assert extract_target(inputs) == "from-host"

        del inputs["host"]
        assert extract_target(inputs) == "from-domain"

    def test_empty_inputs_returns_empty_string(self):
        """An empty inputs dict returns an empty string."""
        assert extract_target({}) == ""

    def test_none_values_skipped(self):
        """None values are skipped, falling through to the next key."""
        inputs = {"target": None, "url": None, "host": "real-host"}
        assert extract_target(inputs) == "real-host"

    def test_empty_string_values_skipped(self):
        """Empty-string values are skipped, falling through to the next key."""
        inputs = {"target": "", "url": "", "domain": "real-domain"}
        assert extract_target(inputs) == "real-domain"

    def test_all_none_returns_empty_string(self):
        """When all keys have None value, an empty string is returned."""
        inputs = {"target": None, "url": None, "host": None, "domain": None}
        assert extract_target(inputs) == ""

    def test_is_pure_function_no_side_effects(self):
        """extract_target does not modify the input dict."""
        inputs = {"target": "https://example.com"}
        original = dict(inputs)
        extract_target(inputs)
        assert inputs == original
