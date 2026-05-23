"""
Tests for scripts/refresh_plugin_checksum.py

What we're testing:
- The digest calculation matches the backend exactly
- A single plugin checksum gets refreshed correctly
- All plugins can be refreshed at once
- The script fails clearly when given invalid paths
- Dry run mode does not write anything
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

# Add repo root to sys.path so we can import the script directly
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))

from scripts.refresh_plugin_checksum import (
    compute_plugin_digest,
    refresh_all_plugins,
    refresh_plugin,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_plugin(tmp_path: Path, plugin_id: str, checksum: str = "old-checksum") -> Path:
    """
    Create a minimal fake plugin folder with metadata.json and parser.py.
    Returns the plugin directory path.
    """
    plugin_dir = tmp_path / plugin_id
    plugin_dir.mkdir()

    metadata = {
        "id": plugin_id,
        "name": f"Test Plugin {plugin_id}",
        "checksum": checksum,
    }
    (plugin_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (plugin_dir / "parser.py").write_text(
        "def parse(output): return []", encoding="utf-8"
    )
    return plugin_dir


# ── compute_plugin_digest ─────────────────────────────────────────────────────

class TestComputePluginDigest:

    def test_returns_a_string(self, tmp_path):
        """Digest should be a non-empty string."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        digest = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )
        assert isinstance(digest, str)
        assert len(digest) > 0

    def test_digest_is_deterministic(self, tmp_path):
        """Same files should always produce the same digest."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        digest1 = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )
        digest2 = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )
        assert digest1 == digest2

    def test_digest_ignores_checksum_field(self, tmp_path):
        """
        The checksum field itself should not affect the digest.
        This is critical — otherwise the digest would change every time
        we write it, creating an infinite loop.
        """
        plugin_dir = make_plugin(tmp_path, "test-plugin", checksum="old-value")
        digest_before = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        # Update the checksum field in metadata
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        metadata["checksum"] = "new-value"
        (plugin_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        digest_after = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        # Digest must be the same — checksum field is stripped before hashing
        assert digest_before == digest_after

    def test_digest_changes_when_metadata_changes(self, tmp_path):
        """Changing a real metadata field should produce a different digest."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        digest_before = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        # Change a real field
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        metadata["name"] = "Changed Name"
        (plugin_dir / "metadata.json").write_text(json.dumps(metadata, indent=2))

        digest_after = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        assert digest_before != digest_after

    def test_digest_changes_when_parser_changes(self, tmp_path):
        """Changing parser.py should produce a different digest."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        digest_before = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        # Change parser.py
        (plugin_dir / "parser.py").write_text("def parse(output): return ['changed']")

        digest_after = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )

        assert digest_before != digest_after

    def test_digest_works_without_parser(self, tmp_path):
        """Digest should still work if parser.py does not exist."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        (plugin_dir / "parser.py").unlink()  # delete parser.py

        digest = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )
        assert isinstance(digest, str)
        assert len(digest) > 0

    def test_matches_backend_logic(self, tmp_path):
        """
        The script digest must match what the backend computes.
        We replicate the backend logic here manually to verify they agree.
        """
        plugin_dir = make_plugin(tmp_path, "test-plugin")
        metadata_file = plugin_dir / "metadata.json"
        parser_file   = plugin_dir / "parser.py"

        # Manually replicate backend logic
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metadata.pop("checksum", None)
        metadata.pop("signature", None)
        canonical = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        metadata_digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        parser_digest   = hashlib.sha256(parser_file.read_bytes()).hexdigest()
        expected = hashlib.sha256(
            f"{metadata_digest}:{parser_digest}".encode("utf-8")
        ).hexdigest()

        actual = compute_plugin_digest(metadata_file, parser_file)
        assert actual == expected


# ── refresh_plugin ────────────────────────────────────────────────────────────

class TestRefreshPlugin:

    def test_updates_checksum_in_metadata(self, tmp_path):
        """After refresh the checksum in metadata.json should be correct."""
        plugin_dir = make_plugin(tmp_path, "test-plugin", checksum="wrong-checksum")

        result = refresh_plugin(plugin_dir)

        assert result is True
        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        expected = compute_plugin_digest(
            plugin_dir / "metadata.json",
            plugin_dir / "parser.py",
        )
        assert metadata["checksum"] == expected

    def test_returns_true_when_already_correct(self, tmp_path):
        """If checksum is already correct refresh_plugin should still return True."""
        plugin_dir = make_plugin(tmp_path, "test-plugin")

        # First refresh to set correct checksum
        refresh_plugin(plugin_dir)

        # Second refresh should still succeed
        result = refresh_plugin(plugin_dir)
        assert result is True

    def test_dry_run_does_not_write(self, tmp_path):
        """Dry run should not modify metadata.json."""
        plugin_dir = make_plugin(tmp_path, "test-plugin", checksum="old-checksum")

        refresh_plugin(plugin_dir, dry_run=True)

        metadata = json.loads((plugin_dir / "metadata.json").read_text())
        # Checksum should still be the old wrong value
        assert metadata["checksum"] == "old-checksum"

    def test_fails_clearly_when_plugin_dir_missing(self, tmp_path):
        """Should return False and not crash if plugin directory doesn't exist."""
        missing_dir = tmp_path / "does-not-exist"
        result = refresh_plugin(missing_dir)
        assert result is False

    def test_fails_clearly_when_metadata_missing(self, tmp_path):
        """Should return False if metadata.json is missing."""
        plugin_dir = tmp_path / "no-metadata"
        plugin_dir.mkdir()
        # No metadata.json created

        result = refresh_plugin(plugin_dir)
        assert result is False

    def test_fails_clearly_when_metadata_is_invalid_json(self, tmp_path):
        """Should return False if metadata.json contains invalid JSON."""
        plugin_dir = tmp_path / "bad-json"
        plugin_dir.mkdir()
        (plugin_dir / "metadata.json").write_text("this is not json", encoding="utf-8")

        result = refresh_plugin(plugin_dir)
        assert result is False


# ── refresh_all_plugins ───────────────────────────────────────────────────────

class TestRefreshAllPlugins:

    def test_refreshes_all_plugins(self, tmp_path):
        """All plugins in the directory should have correct checksums after refresh."""
        # Create three fake plugins with wrong checksums
        for plugin_id in ["plugin-a", "plugin-b", "plugin-c"]:
            make_plugin(tmp_path, plugin_id, checksum="wrong")

        refresh_all_plugins(tmp_path)

        # Verify each plugin now has the correct checksum
        for plugin_id in ["plugin-a", "plugin-b", "plugin-c"]:
            plugin_dir = tmp_path / plugin_id
            metadata = json.loads((plugin_dir / "metadata.json").read_text())
            expected = compute_plugin_digest(
                plugin_dir / "metadata.json",
                plugin_dir / "parser.py",
            )
            assert metadata["checksum"] == expected

    def test_dry_run_does_not_write_any_plugin(self, tmp_path):
        """Dry run should not modify any plugin's metadata.json."""
        for plugin_id in ["plugin-a", "plugin-b"]:
            make_plugin(tmp_path, plugin_id, checksum="old-checksum")

        refresh_all_plugins(tmp_path, dry_run=True)

        for plugin_id in ["plugin-a", "plugin-b"]:
            plugin_dir = tmp_path / plugin_id
            metadata = json.loads((plugin_dir / "metadata.json").read_text())
            assert metadata["checksum"] == "old-checksum"

    def test_exits_when_plugins_dir_missing(self, tmp_path):
        """Should exit with error if plugins directory does not exist."""
        missing_dir = tmp_path / "no-such-dir"

        with pytest.raises(SystemExit):
            refresh_all_plugins(missing_dir)