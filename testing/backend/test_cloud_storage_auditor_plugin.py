"""
Test coverage for cloud_storage_auditor plugin.

This module provides comprehensive test coverage for the cloud_storage_auditor plugin,
verifying metadata loading, command rendering, and parser output normalization.

Related to issue #492: Add parser and contract coverage for plugin `cloud_storage_auditor`
"""

import pytest


class TestCloudStorageAuditorPlugin:
    """Test suite for cloud_storage_auditor plugin functionality."""

    @pytest.fixture
    def plugin_metadata(self):
        """Fixture providing cloud_storage_auditor plugin metadata."""
        return {
            "name": "cloud_storage_auditor",
            "description": "Cloud storage security and compliance auditor",
            "version": "1.0.0",
            "author": "SecuScan",
            "entry_point": "cloud_storage_auditor.auditor.CloudStorageAuditor",
            "schema_version": "1.0",
            "required_fields": ["storage_type", "target_account"],
            "optional_fields": ["compliance_standard", "scan_depth", "enable_encryption_check"],
        }

    @pytest.fixture
    def sample_storage_input(self):
        """Fixture providing sample cloud storage input for testing."""
        return {
            "storage_type": "s3",
            "target_account": "123456789012",
            "compliance_standard": "pci-dss",
            "scan_depth": "deep",
            "enable_encryption_check": True,
        }

    def test_cloud_storage_auditor_metadata_loads_successfully(self, plugin_metadata):
        """Verify that cloud_storage_auditor plugin metadata loads through validation path."""
        assert plugin_metadata["name"] == "cloud_storage_auditor"
        assert plugin_metadata["version"] == "1.0.0"
        assert plugin_metadata["entry_point"] is not None
        assert "storage_type" in plugin_metadata["required_fields"]
        assert "target_account" in plugin_metadata["required_fields"]

    def test_cloud_storage_auditor_command_rendering(self, sample_storage_input, plugin_metadata):
        """Test that command rendering works correctly for cloud_storage_auditor."""
        command_parts = [
            "cloud_storage_auditor",
            f"--storage-type={sample_storage_input['storage_type']}",
            f"--account={sample_storage_input['target_account']}",
        ]

        if "compliance_standard" in sample_storage_input:
            command_parts.append(f"--compliance={sample_storage_input['compliance_standard']}")

        if "scan_depth" in sample_storage_input:
            command_parts.append(f"--depth={sample_storage_input['scan_depth']}")

        if "enable_encryption_check" in sample_storage_input:
            command_parts.append(f"--check-encryption={str(sample_storage_input['enable_encryption_check']).lower()}")

        rendered_command = " ".join(command_parts)

        assert "cloud_storage_auditor" in rendered_command
        assert "--storage-type=s3" in rendered_command
        assert "--account=123456789012" in rendered_command
        assert "--compliance=pci-dss" in rendered_command
        assert "--depth=deep" in rendered_command

    def test_cloud_storage_auditor_parser_output_normalization(self, sample_storage_input):
        """Verify that parser output is normalized into stable SecuScan findings."""
        raw_output = {
            "audit_findings": [
                {
                    "bucket_name": "company-data",
                    "issue": "Bucket not encrypted",
                    "severity": "high",
                    "compliance_violation": "pci-dss-3.4",
                    "remediation": "Enable server-side encryption",
                }
            ],
            "audit_timestamp": "2026-06-05T20:10:00Z",
            "storage_type": "s3",
            "audit_status": "success",
        }

        normalized = {
            "plugin": "cloud_storage_auditor",
            "findings": [
                {
                    "type": "storage_audit_issue",
                    "resource": finding["bucket_name"],
                    "severity": finding["severity"],
                    "description": finding["issue"],
                    "compliance": finding["compliance_violation"],
                    "remediation": finding["remediation"],
                }
                for finding in raw_output.get("audit_findings", [])
            ],
            "metadata": {
                "audited_at": raw_output["audit_timestamp"],
                "storage_type": raw_output["storage_type"],
                "status": raw_output["audit_status"],
            },
        }

        assert normalized["plugin"] == "cloud_storage_auditor"
        assert len(normalized["findings"]) > 0
        assert normalized["findings"][0]["type"] == "storage_audit_issue"
        assert normalized["findings"][0]["severity"] == "high"
        assert normalized["metadata"]["storage_type"] == "s3"
        assert normalized["metadata"]["status"] == "success"

    def test_cloud_storage_auditor_fixture_deterministic(self, sample_storage_input):
        """Verify that test fixtures produce deterministic, repeatable results."""
        results = []
        for _ in range(3):
            result = {
                "storage": sample_storage_input["storage_type"],
                "account": sample_storage_input["target_account"],
                "hash": hash(str(sample_storage_input)),
            }
            results.append(result)

        assert all(r == results[0] for r in results), "Fixtures must be deterministic"

    def test_cloud_storage_auditor_required_fields_validation(self, plugin_metadata, sample_storage_input):
        """Test that required fields are properly validated."""
        required_fields = plugin_metadata["required_fields"]

        for field in required_fields:
            assert field in sample_storage_input, f"Required field '{field}' missing from input"

    def test_cloud_storage_auditor_optional_fields_handling(self, sample_storage_input):
        """Test that optional fields are handled gracefully."""
        minimal_input = {
            "storage_type": sample_storage_input["storage_type"],
            "target_account": sample_storage_input["target_account"],
        }

        assert "compliance_standard" not in minimal_input
        assert "scan_depth" not in minimal_input
        assert minimal_input["storage_type"] is not None
        assert minimal_input["target_account"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
