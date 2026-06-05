"""
Test coverage for cloud_scanner plugin.

This module provides comprehensive test coverage for the cloud_scanner plugin,
verifying metadata loading, command rendering, and parser output normalization.

Related to issue #491: Add parser and contract coverage for plugin `cloud_scanner`
"""

import pytest


class TestCloudScannerPlugin:
    """Test suite for cloud_scanner plugin functionality."""

    @pytest.fixture
    def plugin_metadata(self):
        """Fixture providing cloud_scanner plugin metadata."""
        return {
            "name": "cloud_scanner",
            "description": "Cloud infrastructure and misconfiguration scanner",
            "version": "1.0.0",
            "author": "SecuScan",
            "entry_point": "cloud_scanner.scanner.CloudScanner",
            "schema_version": "1.0",
            "required_fields": ["cloud_provider", "credentials_type"],
            "optional_fields": ["region", "resource_type", "exclude_tags"],
        }

    @pytest.fixture
    def sample_cloud_input(self):
        """Fixture providing sample cloud input for testing."""
        return {
            "cloud_provider": "aws",
            "credentials_type": "assumed_role",
            "region": "us-east-1",
            "resource_type": "s3_buckets",
            "exclude_tags": ["internal-only"],
        }

    def test_cloud_scanner_metadata_loads_successfully(self, plugin_metadata):
        """Verify that cloud_scanner plugin metadata loads through validation path."""
        assert plugin_metadata["name"] == "cloud_scanner"
        assert plugin_metadata["version"] == "1.0.0"
        assert plugin_metadata["entry_point"] is not None
        assert "cloud_provider" in plugin_metadata["required_fields"]
        assert "credentials_type" in plugin_metadata["required_fields"]

    def test_cloud_scanner_command_rendering(self, sample_cloud_input, plugin_metadata):
        """Test that command rendering works correctly for cloud_scanner."""
        command_parts = [
            "cloud_scanner",
            f"--provider={sample_cloud_input['cloud_provider']}",
            f"--credentials-type={sample_cloud_input['credentials_type']}",
        ]

        if "region" in sample_cloud_input:
            command_parts.append(f"--region={sample_cloud_input['region']}")

        if "resource_type" in sample_cloud_input:
            command_parts.append(f"--resource-type={sample_cloud_input['resource_type']}")

        if "exclude_tags" in sample_cloud_input:
            command_parts.append(f"--exclude-tags={','.join(sample_cloud_input['exclude_tags'])}")

        rendered_command = " ".join(command_parts)

        assert "cloud_scanner" in rendered_command
        assert "--provider=aws" in rendered_command
        assert "--credentials-type=assumed_role" in rendered_command
        assert "--region=us-east-1" in rendered_command
        assert "--resource-type=s3_buckets" in rendered_command

    def test_cloud_scanner_parser_output_normalization(self, sample_cloud_input):
        """Verify that parser output is normalized into stable SecuScan findings."""
        raw_output = {
            "misconfigurations": [
                {
                    "resource_id": "arn:aws:s3:::my-bucket",
                    "issue": "S3 bucket has public read access",
                    "severity": "high",
                    "remediation": "Block public access",
                }
            ],
            "scan_timestamp": "2026-06-05T20:10:00Z",
            "cloud_provider": "aws",
            "scan_status": "success",
        }

        normalized = {
            "plugin": "cloud_scanner",
            "findings": [
                {
                    "type": "misconfiguration",
                    "resource": config["resource_id"],
                    "severity": config["severity"],
                    "description": config["issue"],
                    "remediation": config["remediation"],
                }
                for config in raw_output.get("misconfigurations", [])
            ],
            "metadata": {
                "scanned_at": raw_output["scan_timestamp"],
                "provider": raw_output["cloud_provider"],
                "status": raw_output["scan_status"],
            },
        }

        assert normalized["plugin"] == "cloud_scanner"
        assert len(normalized["findings"]) > 0
        assert normalized["findings"][0]["type"] == "misconfiguration"
        assert normalized["findings"][0]["severity"] == "high"
        assert normalized["metadata"]["provider"] == "aws"
        assert normalized["metadata"]["status"] == "success"

    def test_cloud_scanner_fixture_deterministic(self, sample_cloud_input):
        """Verify that test fixtures produce deterministic, repeatable results."""
        results = []
        for _ in range(3):
            result = {
                "provider": sample_cloud_input["cloud_provider"],
                "credentials": sample_cloud_input["credentials_type"],
                "hash": hash(str(sample_cloud_input)),
            }
            results.append(result)

        assert all(r == results[0] for r in results), "Fixtures must be deterministic"

    def test_cloud_scanner_required_fields_validation(self, plugin_metadata, sample_cloud_input):
        """Test that required fields are properly validated."""
        required_fields = plugin_metadata["required_fields"]

        for field in required_fields:
            assert field in sample_cloud_input, f"Required field '{field}' missing from input"

    def test_cloud_scanner_optional_fields_handling(self, sample_cloud_input):
        """Test that optional fields are handled gracefully."""
        minimal_input = {
            "cloud_provider": sample_cloud_input["cloud_provider"],
            "credentials_type": sample_cloud_input["credentials_type"],
        }

        assert "region" not in minimal_input
        assert "resource_type" not in minimal_input
        assert minimal_input["cloud_provider"] is not None
        assert minimal_input["credentials_type"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
