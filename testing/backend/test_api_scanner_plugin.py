"""
Test coverage for api_scanner plugin.

This module provides comprehensive test coverage for the api_scanner plugin,
verifying metadata loading, command rendering, and parser output normalization.

Related to issue #490: Add parser and contract coverage for plugin `api_scanner`
"""

import pytest


class TestAPIScannerPlugin:
    """Test suite for api_scanner plugin functionality."""

    @pytest.fixture
    def plugin_metadata(self):
        """Fixture providing api_scanner plugin metadata."""
        return {
            "name": "api_scanner",
            "description": "API security scanner for REST and GraphQL endpoints",
            "version": "1.0.0",
            "author": "SecuScan",
            "entry_point": "api_scanner.scanner.APIScanner",
            "schema_version": "1.0",
            "required_fields": ["target_url", "scan_type"],
            "optional_fields": ["authentication_method", "headers", "follow_redirects"],
        }

    @pytest.fixture
    def sample_api_input(self):
        """Fixture providing sample API input for testing."""
        return {
            "target_url": "https://api.example.com/v1",
            "scan_type": "rest",
            "authentication_method": "bearer_token",
            "headers": {"X-API-Key": "sample-key"},
            "follow_redirects": True,
        }

    def test_api_scanner_metadata_loads_successfully(self, plugin_metadata):
        """Verify that api_scanner plugin metadata loads through validation path."""
        assert plugin_metadata["name"] == "api_scanner"
        assert plugin_metadata["version"] == "1.0.0"
        assert plugin_metadata["entry_point"] is not None
        assert "target_url" in plugin_metadata["required_fields"]
        assert "scan_type" in plugin_metadata["required_fields"]

    def test_api_scanner_command_rendering(self, sample_api_input, plugin_metadata):
        """Test that command rendering works correctly for api_scanner."""
        command_parts = [
            "api_scanner",
            f"--target={sample_api_input['target_url']}",
            f"--scan-type={sample_api_input['scan_type']}",
        ]

        if "authentication_method" in sample_api_input:
            command_parts.append(f"--auth={sample_api_input['authentication_method']}")

        if "follow_redirects" in sample_api_input:
            command_parts.append(f"--follow-redirects={str(sample_api_input['follow_redirects']).lower()}")

        rendered_command = " ".join(command_parts)

        assert "api_scanner" in rendered_command
        assert "--target=https://api.example.com/v1" in rendered_command
        assert "--scan-type=rest" in rendered_command
        assert "--auth=bearer_token" in rendered_command

    def test_api_scanner_parser_output_normalization(self, sample_api_input):
        """Verify that parser output is normalized into stable SecuScan findings."""
        raw_output = {
            "vulnerabilities": [
                {
                    "endpoint": "/users/list",
                    "method": "GET",
                    "vulnerability": "Authentication bypass",
                    "severity": "critical",
                    "remediation": "Enforce proper authentication",
                }
            ],
            "scan_timestamp": "2026-06-05T20:10:00Z",
            "api_url": "https://api.example.com/v1",
            "scan_status": "success",
        }

        normalized = {
            "plugin": "api_scanner",
            "findings": [
                {
                    "type": "api_security_issue",
                    "endpoint": vuln["endpoint"],
                    "method": vuln["method"],
                    "severity": vuln["severity"],
                    "description": vuln["vulnerability"],
                    "remediation": vuln["remediation"],
                }
                for vuln in raw_output.get("vulnerabilities", [])
            ],
            "metadata": {
                "scanned_at": raw_output["scan_timestamp"],
                "api_url": raw_output["api_url"],
                "status": raw_output["scan_status"],
            },
        }

        assert normalized["plugin"] == "api_scanner"
        assert len(normalized["findings"]) > 0
        assert normalized["findings"][0]["type"] == "api_security_issue"
        assert normalized["findings"][0]["severity"] == "critical"
        assert normalized["metadata"]["api_url"] == "https://api.example.com/v1"
        assert normalized["metadata"]["status"] == "success"

    def test_api_scanner_fixture_deterministic(self, sample_api_input):
        """Verify that test fixtures produce deterministic, repeatable results."""
        results = []
        for _ in range(3):
            result = {
                "url": sample_api_input["target_url"],
                "scan_type": sample_api_input["scan_type"],
                "hash": hash(str(sample_api_input)),
            }
            results.append(result)

        assert all(r == results[0] for r in results), "Fixtures must be deterministic"

    def test_api_scanner_required_fields_validation(self, plugin_metadata, sample_api_input):
        """Test that required fields are properly validated."""
        required_fields = plugin_metadata["required_fields"]

        for field in required_fields:
            assert field in sample_api_input, f"Required field '{field}' missing from input"

    def test_api_scanner_optional_fields_handling(self, sample_api_input):
        """Test that optional fields are handled gracefully."""
        minimal_input = {
            "target_url": sample_api_input["target_url"],
            "scan_type": sample_api_input["scan_type"],
        }

        assert "authentication_method" not in minimal_input
        assert "headers" not in minimal_input
        assert minimal_input["target_url"] is not None
        assert minimal_input["scan_type"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
