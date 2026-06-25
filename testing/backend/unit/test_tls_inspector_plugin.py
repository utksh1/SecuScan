"""Parser fixture coverage for plugins/tls_inspector."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from backend.secuscan.config import settings

PLUGIN_ID = "tls_inspector"
FIXTURE_DIR = Path(__file__).parent / "fixtures" / PLUGIN_ID
PARSER_PATH = Path(settings.plugins_dir) / PLUGIN_ID / "parser.py"


def _load_tls_inspector_parser():
    spec = importlib.util.spec_from_file_location(
        "tls_inspector_parser",
        PARSER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tls_inspector_secure_fixture():
    parser = _load_tls_inspector_parser()

    raw_output = (FIXTURE_DIR / "secure_output.txt").read_text(
        encoding="utf-8"
    )

    parsed = parser.parse(raw_output)

    assert parsed["findings"] == []
    assert parsed["metadata"]["protocol"] == "TLSv1.3"
    assert parsed["metadata"]["certificate_verified"] is True
    assert parsed["metadata"]["has_certificate"] is True


def test_tls_inspector_weak_protocol_fixture():
    parser = _load_tls_inspector_parser()

    raw_output = (FIXTURE_DIR / "weak_tls_output.txt").read_text(
        encoding="utf-8"
    )

    parsed = parser.parse(raw_output)

    assert len(parsed["findings"]) == 1
    assert "Weak TLS Protocol" in parsed["findings"][0]["title"]
    assert parsed["findings"][0]["severity"] == "medium"


def test_tls_inspector_malformed_certificate_fixture():
    parser = _load_tls_inspector_parser()

    raw_output = (FIXTURE_DIR / "malformed_output.txt").read_text(
        encoding="utf-8"
    )

    parsed = parser.parse(raw_output)

    assert parsed["metadata"]["certificate_verified"] is False
    assert len(parsed["findings"]) == 1
    assert parsed["findings"][0]["title"] == "SSL Certificate Validation Failed"