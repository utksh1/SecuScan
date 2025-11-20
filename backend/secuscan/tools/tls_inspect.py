from __future__ import annotations
from typing import Any, Dict


async def run(parameters: Dict[str, Any]) -> Dict[str, Any]:
    host = parameters.get("host", "example.com:443")
    show_chain = bool(parameters.get("show_chain", True))

    chain = [
        {
            "subject": "CN=example.com",
            "issuer": "CN=Stub CA",
            "not_before": "2025-01-01T00:00:00Z",
            "not_after": "2026-01-01T00:00:00Z",
            "signature_algo": "SHA256-RSA",
        }
    ]

    structured = {
        "certificate": {
            "host": host,
            "issuer": "Stub CA",
            "expiry": "2026-01-01T00:00:00Z",
            "signature_algorithm": "SHA256-RSA",
            "san": ["example.com", "www.example.com"],
        },
        "chain": chain if show_chain else [],
        "security": {
            "tls_versions": ["TLS1.2", "TLS1.3"],
            "weak_ciphers": [],
            "warnings": [],
        },
    }
    return {
        "summary": {"description": f"TLS certificate valid for {host}"},
        "structured": structured,
    }

