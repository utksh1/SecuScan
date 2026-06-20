from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from .base import BaseScanner
from ..crawler import crawl_target
from ..plugins import get_plugin_manager


class WebScanner(BaseScanner):
    """
    Orchestrates a layered web assessment using passive evidence first and
    external scanners as corroborating sources.
    """

    SECURITY_HEADERS = {
        "content-security-policy": ("Content-Security-Policy", "medium"),
        "strict-transport-security": ("Strict-Transport-Security", "low"),
        "x-frame-options": ("X-Frame-Options", "low"),
        "x-content-type-options": ("X-Content-Type-Options", "low"),
        "referrer-policy": ("Referrer-Policy", "low"),
        "permissions-policy": ("Permissions-Policy", "info"),
    }

    @property
    def name(self) -> str:
        return "Web Application Scanner"

    @property
    def category(self) -> str:
        return "Web Security"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        intensity = inputs.get("scan_intensity", "light")
        findings: List[Dict[str, Any]] = []
        summary = [f"Performing {intensity} web scan on {target}"]

        extra_headers = (
            inputs.get("__extra_headers")
            if isinstance(inputs.get("__extra_headers"), dict)
            else {}
        )
        cookies = (
            inputs.get("__cookies") if isinstance(inputs.get("__cookies"), dict) else {}
        )

        self.update_progress(0.05)
        crawl = await crawl_target(
            target,
            timeout=int(inputs.get("timeout") or 10),
            cookies=cookies,
            extra_headers=extra_headers,
        )
        findings.extend(self._build_passive_findings(target, crawl))
        summary.append(
            f"Crawler captured {len(crawl.get('pages', []))} pages, {len(crawl.get('forms', []))} forms, and {len(crawl.get('api_hints', []))} API hints."
        )
        self.update_progress(0.3)

        nuclei_findings = await self._run_nuclei(target)
        findings.extend(nuclei_findings)
        if nuclei_findings:
            summary.append(
                f"Discovered {len(nuclei_findings)} template-based observations via Nuclei."
            )
        self.update_progress(0.55)

        if intensity in ["deep", "custom"]:
            nikto_findings = await self._run_nikto(target)
            findings.extend(nikto_findings)
            if nikto_findings:
                summary.append("Completed normalized Nikto server checks.")
            self.update_progress(0.75)

            dir_findings = await self._run_ffuf(target)
            findings.extend(dir_findings)
            if dir_findings:
                summary.append("Enumerated exposed paths and admin/docs surfaces.")
            self.update_progress(1.0)

        rows = []
        for page in crawl.get("pages", [])[:100]:
            rows.append(
                {"type": "page", "url": page.get("url"), "title": page.get("title")}
            )
        for path_hint in crawl.get("path_hints", [])[:50]:
            rows.append({"type": "path_hint", **path_hint})

        self.update_progress(1.0)
        return {
            "findings": findings,
            "summary": summary,
            "status": "completed",
            "crawl": crawl,
            "rows": rows[:150],
        }

    def _build_passive_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        findings.extend(self._surface_findings(target, crawl))
        findings.extend(self._header_findings(target, crawl))
        findings.extend(self._cookie_findings(target, crawl))
        findings.extend(self._form_findings(target, crawl))
        findings.extend(self._path_findings(target, crawl))
        findings.extend(self._transport_findings(target, crawl))
        findings.extend(self._cms_findings(target, crawl))
        return findings

    def _surface_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        forms = crawl.get("forms", [])
        if forms:
            findings.append(
                {
                    "title": "Interactive Forms Discovered",
                    "category": "Attack Surface",
                    "severity": "info",
                    "target": target,
                    "description": f"The crawler discovered {len(forms)} HTML forms that should be included in auth, CSRF, and input-validation review.",
                    "remediation": "Review each form for authentication requirements, CSRF tokens, and server-side validation.",
                    "validated": True,
                    "validation_method": "passive_crawl",
                    "confidence_reason": "Forms were parsed directly from the target HTML during the crawl phase.",
                    "evidence": [
                        {
                            "type": "form",
                            "label": "Form action",
                            "value": form.get("action"),
                            "source": "crawl",
                        }
                        for form in forms[:10]
                    ],
                    "metadata": {"form_count": len(forms)},
                }
            )
        api_hints = crawl.get("api_hints", [])
        if api_hints:
            findings.append(
                {
                    "title": "Potential API Endpoints Discovered",
                    "category": "API Discovery",
                    "severity": "low",
                    "target": target,
                    "description": "The crawl discovered URLs or scripts that look like API, OpenAPI, Swagger, or GraphQL surfaces.",
                    "remediation": "Include these endpoints in authentication, authorization, and schema review coverage.",
                    "validated": True,
                    "validation_method": "passive_crawl",
                    "confidence_reason": "API-like paths were identified from live application responses.",
                    "evidence": [
                        {
                            "type": "url",
                            "label": "API hint",
                            "value": item,
                            "source": "crawl",
                        }
                        for item in api_hints[:10]
                    ],
                    "metadata": {"api_hint_count": len(api_hints)},
                }
            )
        return findings

    def _header_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        headers = {
            str(key).lower(): str(value)
            for key, value in (crawl.get("headers") or {}).items()
        }
        final_url = str(crawl.get("final_url") or target)
        for header_key, (label, severity) in self.SECURITY_HEADERS.items():
            value = headers.get(header_key, "")
            if value:
                continue
            findings.append(
                {
                    "title": f"Missing {label}",
                    "category": "Transport Security",
                    "severity": severity,
                    "target": target,
                    "description": f"The response from {final_url} did not include the {label} security header.",
                    "remediation": f"Set {label} with an application-appropriate policy and verify it across authenticated and unauthenticated routes.",
                    "validated": True,
                    "validation_method": "header_analysis",
                    "confidence_reason": "The header snapshot taken during the crawl did not include this control.",
                    "evidence": [
                        {
                            "type": "url",
                            "label": "Observed URL",
                            "value": final_url,
                            "source": "crawl",
                        },
                        {
                            "type": "header_snapshot",
                            "label": "Header snapshot",
                            "value": json.dumps(headers, sort_keys=True)[:1000],
                            "source": "crawl",
                        },
                    ],
                    "metadata": {"header": label, "url": final_url},
                }
            )

        server = headers.get("server")
        if server:
            findings.append(
                {
                    "title": f"Server Banner Exposed: {server}",
                    "category": "Information Disclosure",
                    "severity": "info",
                    "target": target,
                    "description": "The application exposed a server banner in the HTTP response headers.",
                    "validated": True,
                    "validation_method": "header_analysis",
                    "confidence_reason": "The server banner was observed directly in the HTTP response headers.",
                    "evidence": [
                        {
                            "type": "header",
                            "label": "Server",
                            "value": server,
                            "source": "crawl",
                        }
                    ],
                    "metadata": {"server": server},
                }
            )
        return findings

    def _cookie_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for raw_cookie in crawl.get("set_cookie_headers", [])[:20]:
            parts = [
                segment.strip()
                for segment in str(raw_cookie).split(";")
                if segment.strip()
            ]
            if not parts:
                continue
            cookie_name = parts[0].split("=", 1)[0]
            lowered = {segment.lower() for segment in parts[1:]}
            missing_flags = []
            if "httponly" not in lowered:
                missing_flags.append("HttpOnly")
            if (
                "secure" not in lowered
                and str(crawl.get("scheme") or "").lower() == "https"
            ):
                missing_flags.append("Secure")
            if not any(segment.startswith("samesite=") for segment in lowered):
                missing_flags.append("SameSite")
            if not missing_flags:
                continue
            findings.append(
                {
                    "title": f"Insecure Cookie Attributes on {cookie_name}",
                    "category": "Session Management",
                    "severity": "medium" if "Secure" in missing_flags else "low",
                    "target": target,
                    "description": f"The cookie {cookie_name} was observed without recommended attributes: {', '.join(missing_flags)}.",
                    "remediation": "Set Secure, HttpOnly, and SameSite on session-relevant cookies and verify exceptions intentionally.",
                    "validated": True,
                    "validation_method": "cookie_analysis",
                    "confidence_reason": "Set-Cookie headers were observed directly during the crawl session.",
                    "evidence": [
                        {
                            "type": "set_cookie",
                            "label": "Set-Cookie",
                            "value": raw_cookie,
                            "source": "crawl",
                        }
                    ],
                    "metadata": {
                        "cookie_name": cookie_name,
                        "missing_flags": missing_flags,
                    },
                }
            )
        return findings

    def _form_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for form in crawl.get("forms", [])[:20]:
            action = str(form.get("action") or form.get("page_url") or target)
            if form.get("state_changing") and not form.get("has_csrf_token"):
                findings.append(
                    {
                        "title": f"State-Changing Form Missing CSRF Indicators: {action}",
                        "category": "CSRF",
                        "severity": "medium",
                        "target": target,
                        "description": "A state-changing form was observed without an obvious CSRF token field.",
                        "remediation": "Implement per-request CSRF tokens or an equivalent anti-CSRF control and verify enforcement server-side.",
                        "validated": True,
                        "validation_method": "form_analysis",
                        "confidence_reason": "The form structure was observed directly and no common CSRF token field name was present.",
                        "evidence": [
                            {
                                "type": "form_action",
                                "label": "Form action",
                                "value": action,
                                "source": "crawl",
                            },
                            {
                                "type": "form_method",
                                "label": "Method",
                                "value": form.get("method"),
                                "source": "crawl",
                            },
                        ],
                        "metadata": {"action": action, "method": form.get("method")},
                    }
                )
            if (
                form.get("password_fields")
                and str(crawl.get("scheme") or "").lower() != "https"
            ):
                findings.append(
                    {
                        "title": f"Credential Form Exposed over Non-HTTPS: {action}",
                        "category": "Authentication",
                        "severity": "high",
                        "target": target,
                        "description": "A form containing password inputs was observed without HTTPS protection on the final URL.",
                        "remediation": "Require HTTPS across all authentication flows and redirect all HTTP traffic before credential exchange.",
                        "validated": True,
                        "validation_method": "form_transport_analysis",
                        "confidence_reason": "Password fields were parsed from the form and the final crawl URL was not HTTPS.",
                        "evidence": [
                            {
                                "type": "form_action",
                                "label": "Form action",
                                "value": action,
                                "source": "crawl",
                            },
                            {
                                "type": "scheme",
                                "label": "Observed scheme",
                                "value": crawl.get("scheme"),
                                "source": "crawl",
                            },
                        ],
                        "metadata": {"action": action},
                    }
                )
        return findings

    def _path_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[str]] = {}
        for item in crawl.get("path_hints", []):
            if not isinstance(item, dict):
                continue
            grouped.setdefault(str(item.get("kind") or "path"), []).append(
                str(item.get("url") or "")
            )

        findings: List[Dict[str, Any]] = []
        labels = {
            "admin": ("Administrative Paths Exposed", "medium"),
            "login": ("Authentication Paths Exposed", "info"),
            "debug": ("Debug or Diagnostics Paths Exposed", "medium"),
            "docs": ("Documentation Paths Exposed", "low"),
        }
        for kind, urls in grouped.items():
            if not urls:
                continue
            title, severity = labels.get(kind, ("Interesting Paths Discovered", "info"))
            findings.append(
                {
                    "title": title,
                    "category": "Asset Discovery",
                    "severity": severity,
                    "target": target,
                    "description": f"The crawl or directory discovery workflow located {len(urls)} {kind} path(s) that merit focused review.",
                    "remediation": "Confirm these paths are expected, authenticated where appropriate, and not overexposed to untrusted users.",
                    "validated": True,
                    "validation_method": "surface_discovery",
                    "confidence_reason": "The paths were observed directly during crawl or path enumeration.",
                    "evidence": [
                        {
                            "type": "url",
                            "label": f"{kind.title()} path",
                            "value": url,
                            "source": "crawl",
                        }
                        for url in urls[:10]
                    ],
                    "metadata": {"path_kind": kind, "count": len(urls)},
                }
            )
        return findings

    def _transport_findings(
        self, target: str, crawl: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        seed = str(crawl.get("seed_url") or target)
        final_url = str(crawl.get("final_url") or target)
        scheme = str(crawl.get("scheme") or "").lower()
        redirect_chain = crawl.get("redirect_chain", [])

        if scheme != "https":
            findings.append(
                {
                    "title": "HTTPS Not Enforced",
                    "category": "Transport Security",
                    "severity": "medium",
                    "target": target,
                    "description": "The crawl finished on a non-HTTPS URL, indicating plaintext transport remains available.",
                    "remediation": "Redirect all HTTP traffic to HTTPS and ensure sensitive routes never serve content over plaintext transport.",
                    "validated": True,
                    "validation_method": "transport_analysis",
                    "confidence_reason": "The final crawl URL was observed directly and did not use HTTPS.",
                    "evidence": [
                        {
                            "type": "seed_url",
                            "label": "Seed URL",
                            "value": seed,
                            "source": "crawl",
                        },
                        {
                            "type": "final_url",
                            "label": "Final URL",
                            "value": final_url,
                            "source": "crawl",
                        },
                    ],
                    "metadata": {"seed_url": seed, "final_url": final_url},
                }
            )

        if (
            seed.startswith("http://")
            and final_url.startswith("https://")
            and not redirect_chain
        ):
            findings.append(
                {
                    "title": "HTTPS Redirect Chain Incomplete",
                    "category": "Transport Security",
                    "severity": "low",
                    "target": target,
                    "description": "The target ended on HTTPS but no redirect history was recorded, which may indicate inconsistent redirect behavior.",
                    "validated": True,
                    "validation_method": "redirect_analysis",
                    "confidence_reason": "The seed and final URLs differed in transport without a captured redirect chain.",
                    "evidence": [
                        {
                            "type": "seed_url",
                            "label": "Seed URL",
                            "value": seed,
                            "source": "crawl",
                        },
                        {
                            "type": "final_url",
                            "label": "Final URL",
                            "value": final_url,
                            "source": "crawl",
                        },
                    ],
                    "metadata": {"seed_url": seed, "final_url": final_url},
                }
            )
        return findings

    def _cms_findings(self, target: str, crawl: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for cms in crawl.get("cms_hints", [])[:5]:
            findings.append(
                {
                    "title": f"CMS Fingerprint Detected: {str(cms).title()}",
                    "category": "Technology Fingerprint",
                    "severity": "info",
                    "target": target,
                    "description": "The crawl artifacts contained CMS-specific indicators that can be routed into targeted component validation.",
                    "validated": True,
                    "validation_method": "cms_fingerprint",
                    "confidence_reason": "CMS-specific paths, meta generator tags, or static assets were observed during crawl.",
                    "evidence": [
                        {
                            "type": "cms_hint",
                            "label": "CMS hint",
                            "value": cms,
                            "source": "crawl",
                        }
                    ],
                    "metadata": {"cms": cms},
                }
            )
        return findings

    async def _run_nuclei(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("nuclei", {"target": target, "silent": True})
        if not cmd:
            return []

        output, _ = await self._execute_command(cmd)
        findings: List[Dict[str, Any]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            info = item.get("info", {}) if isinstance(item.get("info"), dict) else {}
            template_id = (
                item.get("template-id")
                or item.get("templateID")
                or info.get("name")
                or "nuclei-template"
            )
            severity = self.normalize_severity(
                str(info.get("severity") or item.get("severity") or "info")
            )
            matched = item.get("matched-at") or item.get("matched")
            findings.append(
                {
                    "title": f"Nuclei: {info.get('name') or template_id}",
                    "category": "Vulnerability",
                    "severity": severity,
                    "target": target,
                    "description": str(
                        info.get("description")
                        or item.get("matcher-name")
                        or f"Template {template_id} matched on the target."
                    ),
                    "validated": False,
                    "validation_method": "template_scan",
                    "confidence_reason": "Issue was reported by a Nuclei template and should be corroborated before remediation is prioritized.",
                    "evidence": [
                        {
                            "type": "template",
                            "label": "Template",
                            "value": template_id,
                            "source": "nuclei",
                        },
                        {
                            "type": "url",
                            "label": "Matched URL",
                            "value": matched,
                            "source": "nuclei",
                        },
                    ],
                    "references": [
                        {"source": "template", "url": ref}
                        for ref in info.get("reference", [])
                        if isinstance(ref, str)
                    ],
                    "metadata": {
                        "template": template_id,
                        "url": matched,
                        "source": "nuclei",
                    },
                }
            )

        if findings:
            return findings

        for line in output.splitlines():
            if match := re.match(r"\[(.*?)\] \[(.*?)\] \[(.*?)\] (.*)", line):
                template_id, severity, matched, message = match.groups()
                findings.append(
                    {
                        "title": f"Nuclei: {message}",
                        "category": "Vulnerability",
                        "severity": self.normalize_severity(severity),
                        "target": target,
                        "description": f"Template {template_id} detected a {severity} issue on {matched}.",
                        "validated": False,
                        "validation_method": "template_scan",
                        "confidence_reason": "Issue was reported by a Nuclei template and should be corroborated before remediation is prioritized.",
                        "evidence": [
                            {
                                "type": "template",
                                "label": "Template",
                                "value": template_id,
                                "source": "nuclei",
                            },
                            {
                                "type": "url",
                                "label": "Matched URL",
                                "value": matched,
                                "source": "nuclei",
                            },
                        ],
                        "metadata": {
                            "template": template_id,
                            "url": matched,
                            "source": "nuclei",
                        },
                    }
                )
        return findings

    async def _run_nikto(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("nikto", {"target": target})
        if not cmd:
            return []
        output, _ = await self._execute_command(cmd)
        findings: List[Dict[str, Any]] = []

        try:
            document = json.loads(output)
        except json.JSONDecodeError:
            document = None

        if isinstance(document, dict):
            vulnerabilities = (
                document.get("vulnerabilities")
                or document.get("findings")
                or document.get("items")
                or []
            )
            if isinstance(vulnerabilities, list):
                for item in vulnerabilities:
                    if not isinstance(item, dict):
                        continue
                    uri = item.get("uri") or item.get("url") or item.get("path")
                    message = (
                        item.get("msg")
                        or item.get("message")
                        or item.get("description")
                        or "Nikto observation"
                    )
                    findings.append(
                        {
                            "title": f"Nikto: {message}",
                            "category": "Web Vulnerability",
                            "severity": self.normalize_severity(
                                str(item.get("severity") or "medium")
                            ),
                            "target": target,
                            "description": str(message),
                            "validated": False,
                            "validation_method": "nikto_scan",
                            "confidence_reason": "Observation was reported by Nikto and may require manual confirmation.",
                            "evidence": [
                                {
                                    "type": "url",
                                    "label": "Affected URL",
                                    "value": uri,
                                    "source": "nikto",
                                },
                                {
                                    "type": "nikto_item",
                                    "label": "Nikto record",
                                    "value": json.dumps(item, sort_keys=True)[:1000],
                                    "source": "nikto",
                                },
                            ],
                            "metadata": {"source": "nikto", "url": uri},
                        }
                    )
            if findings:
                return findings

        for line in output.splitlines():
            if "+ " not in line:
                continue
            message = line.replace("+ ", "").strip()
            findings.append(
                {
                    "title": "Nikto Observation",
                    "category": "Web Vulnerability",
                    "severity": "medium",
                    "target": target,
                    "description": message,
                    "validated": False,
                    "validation_method": "nikto_scan",
                    "confidence_reason": "Observation was reported by Nikto and may require manual confirmation.",
                    "evidence": [
                        {
                            "type": "nikto_line",
                            "label": "Nikto output",
                            "value": line.strip(),
                            "source": "nikto",
                        }
                    ],
                    "metadata": {"source": "nikto"},
                }
            )
        return findings

    async def _run_ffuf(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("dir_discovery", {"base_url": target})
        if not cmd:
            return []
        output, _ = await self._execute_command(cmd)
        findings: List[Dict[str, Any]] = []

        try:
            document = json.loads(output)
        except json.JSONDecodeError:
            document = None

        if isinstance(document, dict) and isinstance(document.get("results"), list):
            for item in document["results"]:
                if not isinstance(item, dict):
                    continue
                url = item.get("url")
                status = item.get("status")
                kind = self._classify_path(str(url or "").lower())
                findings.append(
                    {
                        "title": f"Discovered Path: {url}",
                        "category": "Asset Discovery",
                        "severity": "low"
                        if kind in {"admin", "debug", "docs"}
                        else "info",
                        "target": target,
                        "description": f"Accessible path found during fuzzing: {url}",
                        "validated": True,
                        "validation_method": "directory_fuzzing",
                        "confidence_reason": "The endpoint returned an HTTP success or redirect status during path enumeration.",
                        "evidence": [
                            {
                                "type": "url",
                                "label": "Path",
                                "value": url,
                                "source": "ffuf",
                            },
                            {
                                "type": "status_code",
                                "label": "Status",
                                "value": status,
                                "source": "ffuf",
                            },
                        ],
                        "metadata": {
                            "status": status,
                            "path_kind": kind or "generic",
                            "source": "ffuf",
                        },
                    }
                )
            if findings:
                return findings

        for match in re.finditer(
            r"\[Status: (\d+), Size: \d+, Words: \d+, Lines: \d+, Duration: .*?\]\s*\|\s*URL: (.*)",
            output,
        ):
            status, url = match.groups()
            kind = self._classify_path(url.lower())
            findings.append(
                {
                    "title": f"Discovered Path: {url} (Status {status})",
                    "category": "Asset Discovery",
                    "severity": "low" if kind in {"admin", "debug", "docs"} else "info",
                    "target": target,
                    "description": f"Accessible path found during fuzzing: {url}",
                    "validated": True,
                    "validation_method": "directory_fuzzing",
                    "confidence_reason": "The endpoint returned an HTTP success or redirect status during path enumeration.",
                    "evidence": [
                        {
                            "type": "url",
                            "label": "Path",
                            "value": url,
                            "source": "ffuf",
                        },
                        {
                            "type": "status_code",
                            "label": "Status",
                            "value": status,
                            "source": "ffuf",
                        },
                    ],
                    "metadata": {
                        "status": status,
                        "path_kind": kind or "generic",
                        "source": "ffuf",
                    },
                }
            )
        return findings

    def _classify_path(self, value: str) -> str | None:
        if any(token in value for token in ("/admin", "/wp-admin", "/administrator")):
            return "admin"
        if any(token in value for token in ("/debug", "/console", "/actuator")):
            return "debug"
        if any(token in value for token in ("/docs", "/swagger", "/openapi", "/redoc")):
            return "docs"
        if any(token in value for token in ("/login", "/signin", "/auth")):
            return "login"
        return None
