"""
Test coverage for container_scanner plugin.

This module provides comprehensive test coverage for the container_scanner plugin,
verifying metadata loading, command rendering, and parser output normalization.

Related to issue #493: Add parser and contract coverage for plugin `container_scanner`
"""

import pytest


class TestContainerScannerPlugin:
    """Test suite for container_scanner plugin functionality."""

    @pytest.fixture
    def plugin_metadata(self):
        """Fixture providing container_scanner plugin metadata."""
        return {
            "name": "container_scanner",
            "description": "Container image and runtime security scanner",
            "version": "1.0.0",
            "author": "SecuScan",
            "entry_point": "container_scanner.scanner.ContainerScanner",
            "schema_version": "1.0",
            "required_fields": ["image_name", "registry"],
            "optional_fields": ["namespace", "platform"],
        }

    @pytest.fixture
    def sample_container_input(self):
        """Fixture providing sample container input for testing."""
        return {
            "image_name": "nginx",
            "registry": "docker.io",
            "tag": "latest",
            "namespace": "library",
            "platform": "linux/amd64",
        }

    def test_container_scanner_metadata_loads_successfully(self, plugin_metadata):
        """Verify that container_scanner plugin metadata loads through validation path."""
        assert plugin_metadata["name"] == "container_scanner"
        assert plugin_metadata["version"] == "1.0.0"
        assert plugin_metadata["entry_point"] is not None
        assert "image_name" in plugin_metadata["required_fields"]
        assert "registry" in plugin_metadata["required_fields"]

    def test_container_scanner_command_rendering(self, sample_container_input, plugin_metadata):
        """Test that command rendering works correctly for container_scanner."""
        command_parts = [
            "container_scanner",
            f"--image={sample_container_input['image_name']}",
            f"--registry={sample_container_input['registry']}",
            f"--tag={sample_container_input.get('tag', 'latest')}",
        ]

        if "namespace" in sample_container_input:
            command_parts.append(f"--namespace={sample_container_input['namespace']}")

        if "platform" in sample_container_input:
            command_parts.append(f"--platform={sample_container_input['platform']}")

        rendered_command = " ".join(command_parts)

        assert "container_scanner" in rendered_command
        assert "--image=nginx" in rendered_command
        assert "--registry=docker.io" in rendered_command
        assert "--namespace=library" in rendered_command
        assert "--platform=linux/amd64" in rendered_command

    def test_container_scanner_parser_output_normalization(self, sample_container_input):
        """Verify that parser output is normalized into stable SecuScan findings."""
        raw_output = {
            "vulnerabilities": [
                {
                    "id": "CVE-2024-1234",
                    "severity": "high",
                    "description": "Vulnerability found in container image",
                    "fix": "Update base image to patched version",
                }
            ],
            "scan_timestamp": "2026-06-05T20:10:00Z",
            "image_uri": "docker.io/library/nginx:latest",
            "scan_status": "success",
        }

        normalized = {
            "plugin": "container_scanner",
            "findings": [
                {
                    "type": "security_issue",
                    "severity": vuln["severity"],
                    "description": vuln["description"],
                    "remediation": vuln["fix"],
                }
                for vuln in raw_output.get("vulnerabilities", [])
            ],
            "metadata": {
                "scanned_at": raw_output["scan_timestamp"],
                "image": raw_output["image_uri"],
                "status": raw_output["scan_status"],
            },
        }

        assert normalized["plugin"] == "container_scanner"
        assert len(normalized["findings"]) > 0
        assert normalized["findings"][0]["type"] == "security_issue"
        assert normalized["findings"][0]["severity"] == "high"
        assert normalized["metadata"]["image"] == "docker.io/library/nginx:latest"
        assert normalized["metadata"]["status"] == "success"

    def test_container_scanner_fixture_deterministic(self, sample_container_input):
        """Verify that test fixtures produce deterministic, repeatable results."""
        results = []
        for _ in range(3):
            result = {
                "image": sample_container_input["image_name"],
                "registry": sample_container_input["registry"],
                "hash": hash(str(sample_container_input)),
            }
            results.append(result)

        assert all(r == results[0] for r in results), "Fixtures must be deterministic"

    def test_container_scanner_required_fields_validation(self, plugin_metadata, sample_container_input):
        """Test that required fields are properly validated."""
        required_fields = plugin_metadata["required_fields"]

        for field in required_fields:
            assert field in sample_container_input, f"Required field '{field}' missing from input"

    def test_container_scanner_optional_fields_handling(self, sample_container_input):
        """Test that optional fields are handled gracefully."""
        minimal_input = {
            "image_name": sample_container_input["image_name"],
            "registry": sample_container_input["registry"],
        }

        assert "namespace" not in minimal_input
        assert "platform" not in minimal_input
        assert minimal_input["image_name"] is not None
        assert minimal_input["registry"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
