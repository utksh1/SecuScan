"""
Unit tests for scripts/sign_plugins.py

Tests the plugin signing logic: HMAC-SHA256 digest computation
and checksum generation.
"""

import hashlib
import hmac
import json
import sys
import pathlib
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent.parent))
from backend.secuscan.plugins import PluginManager


class TestPluginDigest:
    def test_digest_is_sha256_hex(self, tmp_path):
        metadata_file = tmp_path / "metadata.json"
        parser_file = tmp_path / "parser.py"
        metadata_file.write_text('{"name": "test"}')
        parser_file.write_text("print('hello')")
        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        assert len(digest) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in digest)

    def test_digest_changes_with_content(self, tmp_path):
        metadata_a = tmp_path / "a" / "metadata.json"
        parser_a = tmp_path / "a" / "parser.py"
        parser_a.parent.mkdir()
        metadata_a.write_text('{"name": "a"}')
        parser_a.write_text("print('a')")
        digest_a = PluginManager.compute_plugin_digest(metadata_a, parser_a)

        metadata_b = tmp_path / "b" / "metadata.json"
        parser_b = tmp_path / "b" / "parser.py"
        parser_b.parent.mkdir()
        metadata_b.write_text('{"name": "b"}')
        parser_b.write_text("print('b')")
        digest_b = PluginManager.compute_plugin_digest(metadata_b, parser_b)

        assert digest_a != digest_b


class TestPluginSignature:
    def test_hmac_signature_format(self, tmp_path):
        metadata_file = tmp_path / "metadata.json"
        parser_file = tmp_path / "parser.py"
        metadata_file.write_text('{"name": "test"}')
        parser_file.write_text("print('hello')")
        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        key = "test-secret-key"
        sig = hmac.new(key.encode("utf-8"), digest.encode("utf-8"), hashlib.sha256).hexdigest()
        assert len(sig) == 64
        assert all(c in "0123456789abcdef" for c in sig)

    def test_hmac_is_deterministic(self, tmp_path):
        metadata_file = tmp_path / "metadata.json"
        parser_file = tmp_path / "parser.py"
        metadata_file.write_text('{"name": "test"}')
        parser_file.write_text("print('hello')")
        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        key = "secret"
        sig1 = hmac.new(key.encode(), digest.encode(), hashlib.sha256).hexdigest()
        sig2 = hmac.new(key.encode(), digest.encode(), hashlib.sha256).hexdigest()
        assert sig1 == sig2

    def test_different_keys_produce_different_signatures(self, tmp_path):
        metadata_file = tmp_path / "metadata.json"
        parser_file = tmp_path / "parser.py"
        metadata_file.write_text('{"name": "test"}')
        parser_file.write_text("print('hello')")
        digest = PluginManager.compute_plugin_digest(metadata_file, parser_file)
        sig1 = hmac.new(b"key1", digest.encode(), hashlib.sha256).hexdigest()
        sig2 = hmac.new(b"key2", digest.encode(), hashlib.sha256).hexdigest()
        assert sig1 != sig2
