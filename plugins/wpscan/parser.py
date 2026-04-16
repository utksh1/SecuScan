import json
from typing import Any, Dict, List


def _finding(title: str, category: str, severity: str, description: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "title": title,
        "category": category,
        "severity": severity,
        "description": description,
        "remediation": "Validate exposure and patch vulnerable components.",
        "metadata": metadata or {},
    }


def parse(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []

    try:
        data = json.loads(output)
    except Exception:
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            findings.append(
                _finding(
                    title="WordPress Finding",
                    category="CMS Security",
                    severity="low",
                    description=line,
                    metadata={"source": "stdout"},
                )
            )
        return {"findings": findings, "count": len(findings)}

    for item in data.get("interesting_findings", []):
        title = str(item.get("to_s") or "Interesting WordPress Finding")
        findings.append(
            _finding(
                title=title,
                category="CMS Exposure",
                severity="low",
                description=title,
                metadata={"references": item.get("references", {})},
            )
        )

    plugins = data.get("plugins", {}) or {}
    for plugin_name, plugin_data in plugins.items():
        for vuln in plugin_data.get("vulnerabilities", []) or []:
            vuln_title = vuln.get("title") or "Known plugin vulnerability"
            findings.append(
                _finding(
                    title=f"WordPress Plugin Vulnerability: {plugin_name}",
                    category="CMS Vulnerability",
                    severity="high",
                    description=str(vuln_title),
                    metadata={
                        "component": plugin_name,
                        "component_type": "plugin",
                        "fixed_in": vuln.get("fixed_in"),
                        "references": vuln.get("references", {}),
                    },
                )
            )

    themes = data.get("themes", {}) or {}
    for theme_name, theme_data in themes.items():
        for vuln in theme_data.get("vulnerabilities", []) or []:
            vuln_title = vuln.get("title") or "Known theme vulnerability"
            findings.append(
                _finding(
                    title=f"WordPress Theme Vulnerability: {theme_name}",
                    category="CMS Vulnerability",
                    severity="high",
                    description=str(vuln_title),
                    metadata={
                        "component": theme_name,
                        "component_type": "theme",
                        "fixed_in": vuln.get("fixed_in"),
                        "references": vuln.get("references", {}),
                    },
                )
            )

    return {
        "findings": findings,
        "count": len(findings),
        "target_url": data.get("target_url"),
    }
