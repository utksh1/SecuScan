from __future__ import annotations

import re
import shutil
from typing import Any, Dict, List

from .base import BaseScanner
from ..crawler import crawl_target


class ZAPScanner(BaseScanner):
    """Container-oriented ZAP baseline/passive orchestration."""

    @property
    def name(self) -> str:
        return "OWASP ZAP Orchestrator"

    @property
    def category(self) -> str:
        return "DAST"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        timeout = int(inputs.get("timeout") or 15)
        findings: List[Dict[str, Any]] = []

        self.update_progress(0.15)
        crawl = await crawl_target(target, timeout=timeout)
        findings.extend(self._build_passive_findings(target, crawl))

        raw_output = ""
        if shutil.which("docker"):
            self.update_progress(0.45)
            command = [
                "docker",
                "run",
                "--rm",
                "ghcr.io/zaproxy/zaproxy:stable",
                "zap-baseline.py",
                "-t",
                target,
                "-m",
                str(min(timeout, 5)),
            ]
            raw_output, exit_code = await self._execute_command(command)
            findings.extend(self._parse_zap_output(target, raw_output))
            status = "completed" if exit_code == 0 else "failed"
        else:
            status = "completed"

        self.update_progress(1.0)
        return {
            "status": status,
            "summary": [
                f"DAST orchestration finished for {target}.",
                "Passive crawl evidence was captured and ZAP baseline execution was attempted when Docker was available.",
            ],
            "findings": findings,
            "crawl": crawl,
            "zap_output_excerpt": raw_output[:4000],
            "rows": [{"url": page.get("url"), "type": "page"} for page in crawl.get("pages", [])[:100]],
        }

    def _build_passive_findings(self, target: str, crawl: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        forms = crawl.get("forms", [])
        if forms:
            findings.append(
                {
                    "title": "Interactive Forms Discovered",
                    "category": "Attack Surface",
                    "severity": "info",
                    "target": target,
                    "description": f"The crawler discovered {len(forms)} HTML forms that should be included in authenticated and DAST coverage.",
                    "remediation": "Review form actions for access control, CSRF protection, and input validation coverage.",
                    "validated": True,
                    "validation_method": "passive_crawl",
                    "confidence_reason": "Forms were parsed directly from the target HTML surface.",
                    "evidence": [{"type": "form", "value": form.get("action")} for form in forms[:10]],
                    "references": [],
                    "metadata": {"form_count": len(forms)},
                }
            )
        return findings

    def _parse_zap_output(self, target: str, output: str) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for line in output.splitlines():
            text = line.strip()
            if not text:
                continue
            match = re.search(r"(?i)(FAIL|WARN)-NEW:\s*(.*?)\s*\[(.*?)\]", text)
            if not match:
                continue
            kind, title, ref = match.groups()
            findings.append(
                {
                    "title": f"ZAP {kind.title()}: {title}",
                    "category": "DAST",
                    "severity": "high" if kind.upper() == "FAIL" else "medium",
                    "target": target,
                    "description": text,
                    "remediation": "Validate the ZAP alert, confirm scope, and remediate the affected application behavior.",
                    "validated": False,
                    "validation_method": "zap_baseline",
                    "confidence_reason": "The issue was reported by the ZAP baseline container output.",
                    "evidence": [{"type": "zap_output", "value": text}],
                    "references": [{"source": "ZAP", "id": ref}],
                    "metadata": {"alert_ref": ref},
                }
            )
        return findings
