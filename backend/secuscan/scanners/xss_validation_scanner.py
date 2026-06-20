from __future__ import annotations

from html import escape
from typing import Any, Dict, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from .base import BaseScanner


class XSSValidationScanner(BaseScanner):
    """Bounded reflected-XSS validation with local evidence only."""

    MARKER = "SECUSCAN_XSS_MARKER"
    PAYLOAD = "<script>SECUSCAN_XSS_MARKER</script>"

    @property
    def name(self) -> str:
        return "XSS Validation Scanner"

    @property
    def category(self) -> str:
        return "Web Validation"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        probe_url = self._build_probe_url(target)
        findings: List[Dict[str, Any]] = []
        self.update_progress(0.25)

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=int(inputs.get("timeout") or 10),
            verify=False,
        ) as client:
            response = await client.get(probe_url)

        body = response.text
        reflected_raw = self.PAYLOAD in body
        reflected_marker = self.MARKER in body
        escaped_payload = escape(self.PAYLOAD) in body

        if reflected_raw or reflected_marker or escaped_payload:
            findings.append(
                {
                    "title": "Reflected Input Detected During XSS Validation",
                    "category": "Cross-Site Scripting",
                    "severity": "high" if reflected_raw else "medium",
                    "target": target,
                    "description": "User-controlled input was reflected by the application during bounded XSS validation.",
                    "remediation": "Apply context-aware output encoding and validate untrusted parameters before reflection.",
                    "validated": reflected_raw,
                    "validation_method": "bounded_reflection_probe",
                    "confidence_reason": (
                        "The application reflected the raw script payload."
                        if reflected_raw
                        else "The application reflected the probe marker or an escaped payload, indicating a candidate XSS sink."
                    ),
                    "evidence": [
                        {"type": "url", "value": probe_url},
                        {"type": "status_code", "value": response.status_code},
                        {"type": "marker_reflected", "value": reflected_marker},
                        {"type": "raw_payload_reflected", "value": reflected_raw},
                    ],
                    "references": [],
                    "proof": body[:500],
                    "metadata": {"probe_url": probe_url},
                }
            )

        self.update_progress(1.0)
        return {
            "status": "completed",
            "summary": [
                f"Reflected-XSS validation completed for {target}.",
                f"Captured {len(findings)} bounded validation observations without external exfiltration.",
            ],
            "findings": findings,
            "rows": [
                {
                    "url": probe_url,
                    "status_code": response.status_code,
                    "reflected_raw": reflected_raw,
                }
            ],
        }

    def _build_probe_url(self, target: str) -> str:
        parsed = urlparse(target)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        if not query:
            query["secuscan_probe"] = self.PAYLOAD
        else:
            for key in list(query.keys()):
                query[key] = self.PAYLOAD
        return urlunparse(parsed._replace(query=urlencode(query)))
