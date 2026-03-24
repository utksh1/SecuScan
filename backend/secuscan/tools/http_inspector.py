from __future__ import annotations
from typing import Any, Dict


async def run(parameters: Dict[str, Any]) -> Dict[str, Any]:
    # Stubbed implementation: returns deterministic structure for demos
    url = parameters.get("url", "http://localhost")
    follow = bool(parameters.get("follow_redirects", True))
    timeout = int(parameters.get("timeout", 10))

    structured = {
        "response": {
            "status_code": 200,
            "headers": {"server": "stub/1.0", "content-type": "text/html"},
            "cookies": [],
            "redirect_chain": [] if follow else None,
        },
        "security_analysis": {
            "missing_headers": ["Content-Security-Policy"],
            "insecure_cookies": [],
            "tls_issues": [],
            "score": 85,
        },
    }
    return {
        "summary": {"description": f"HTTP check OK for {url}"},
        "structured": structured,
    }

