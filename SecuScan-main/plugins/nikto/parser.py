import json
import re
from typing import Any, Dict, Iterable, List, Optional


REFERENCE_RE = re.compile(r"\b(?:See|Reference|References):\s*(.+)$", re.IGNORECASE)
JSON_BLOCK_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def parse(output: str) -> Dict[str, Any]:
    """
    Parse Nikto output into SecuScan findings.

    Nikto can emit JSON with -Format json, but older wrappers and some runtime
    failures still produce the classic text report. Support both so the plugin
    remains useful even when Nikto prints banners or warnings around JSON.
    """
    data = _load_json_payload(output)
    if data is not None:
        return _parse_json_output(data, output)

    return _parse_text_output(output)


def _load_json_payload(output: str) -> Optional[Any]:
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        pass

    match = JSON_BLOCK_RE.search(output)
    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _parse_json_output(data: Any, raw_output: str) -> Dict[str, Any]:
    vulnerabilities = list(_iter_vulnerabilities(data))
    findings = [_finding_from_vulnerability(vuln, idx) for idx, vuln in enumerate(vulnerabilities, start=1)]

    return {
        "findings": findings,
        "count": len(findings),
        "target": _extract_json_target(data),
        "raw": raw_output if not findings else None,
    }


def _iter_vulnerabilities(data: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(data, dict):
        return

    for key in ("vulnerabilities", "findings", "issues", "results"):
        value = data.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    yield item
            return

    # Some Nikto JSON variants nest scan data under host-like keys.
    for value in data.values():
        if isinstance(value, dict):
            nested = value.get("vulnerabilities") or value.get("findings") or value.get("results")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        yield item


def _finding_from_vulnerability(vuln: Dict[str, Any], index: int) -> Dict[str, Any]:
    message = _first_string(vuln, "msg", "message", "description", "Description") or "Nikto finding"
    url = _first_string(vuln, "url", "uri", "path", "URL")
    method = _first_string(vuln, "method", "Method")
    nikto_id = _first_string(vuln, "id", "nikto_id", "NiktoID")
    osvdb = _first_string(vuln, "osvdb", "OSVDB", "osvdb_id")
    references = _first_string(vuln, "references", "reference", "References")

    proof_parts = []
    if method:
        proof_parts.append(method)
    if url:
        proof_parts.append(url)
    proof = " ".join(proof_parts) or None

    metadata = {key: value for key, value in vuln.items() if value not in (None, "")}
    if references:
        metadata["references"] = references

    return {
        "title": _title_from_message(message, index),
        "category": _category_from_message(message),
        "severity": _severity_from_message(message),
        "description": _description(message, osvdb, nikto_id, references),
        "remediation": _remediation_for_message(message),
        "proof": proof,
        "metadata": metadata,
    }


def _parse_text_output(output: str) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}
    summary: List[str] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        clean = line[2:].strip() if line.startswith("+ ") else line
        if _is_banner_or_separator(clean):
            continue

        key, value = _split_status_line(clean)
        if key:
            normalized_key = key.lower().replace(" ", "_")
            if normalized_key in {"target_ip", "target_hostname", "target_port", "start_time", "end_time"}:
                metadata[normalized_key] = value
                continue
            if normalized_key == "server":
                findings.append(_text_finding("Server banner disclosed", value, proof=clean))
                continue

        if _is_summary_line(clean):
            summary.append(clean)
            continue

        if line.startswith("+ "):
            parsed = _parse_finding_line(clean, len(findings) + 1)
            if parsed:
                findings.append(parsed)

    result: Dict[str, Any] = {
        "findings": findings,
        "count": len(findings),
        "metadata": metadata,
        "summary": summary,
    }
    if not findings:
        result["raw"] = output
    return result


def _parse_finding_line(line: str, index: int) -> Optional[Dict[str, Any]]:
    if _is_non_finding_status(line):
        return None

    proof = line
    target_part = None
    message = line

    if ": " in line:
        possible_target, possible_message = line.split(": ", 1)
        if possible_target.startswith(("/", "http://", "https://")):
            target_part = possible_target
            message = possible_message

    references = None
    ref_match = REFERENCE_RE.search(message)
    if ref_match:
        references = ref_match.group(1).strip()
        message = REFERENCE_RE.sub("", message).strip(" .")

    return {
        "title": _title_from_message(message, index),
        "category": _category_from_message(message),
        "severity": _severity_from_message(message),
        "description": _description(message, references=references),
        "remediation": _remediation_for_message(message),
        "proof": proof,
        "metadata": {
            "path": target_part,
            "references": references,
        },
    }


def _text_finding(title: str, message: str, proof: Optional[str] = None) -> Dict[str, Any]:
    return {
        "title": title,
        "category": "Information Disclosure",
        "severity": "low",
        "description": f"Nikto reported: {message}",
        "remediation": "Review whether this server information should be exposed to unauthenticated users.",
        "proof": proof,
        "metadata": {},
    }


def _split_status_line(line: str) -> tuple[Optional[str], Optional[str]]:
    if ":" not in line:
        return None, None
    key, value = line.split(":", 1)
    key = key.strip()
    value = value.strip()
    if not key or not value:
        return None, None
    return key, value


def _is_banner_or_separator(line: str) -> bool:
    return (
        line.startswith("-")
        or line.lower().startswith("nikto v")
        or line.lower().startswith("copyright")
        or line.lower().startswith("option ")
    )


def _is_summary_line(line: str) -> bool:
    lower = line.lower()
    return "item(s) reported" in lower or lower.startswith("scan terminated")


def _is_non_finding_status(line: str) -> bool:
    lower = line.lower()
    prefixes = (
        "target ip:",
        "target hostname:",
        "target port:",
        "start time:",
        "end time:",
        "no web server found",
        "error:",
    )
    return lower.startswith(prefixes) or _is_summary_line(line)


def _first_string(data: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return str(value)
    return None


def _extract_json_target(data: Any) -> Optional[str]:
    if not isinstance(data, dict):
        return None
    for key in ("host", "hostname", "target", "url", "ip"):
        value = data.get(key)
        if value:
            return str(value)
    return None


def _title_from_message(message: str, index: int) -> str:
    title = " ".join(message.split())
    if len(title) > 110:
        title = title[:107].rstrip() + "..."
    return title or f"Nikto finding #{index}"


def _description(
    message: str,
    osvdb: Optional[str] = None,
    nikto_id: Optional[str] = None,
    references: Optional[str] = None,
) -> str:
    parts = [message]
    if nikto_id:
        parts.append(f"Nikto ID: {nikto_id}.")
    if osvdb:
        parts.append(f"OSVDB ID: {osvdb}.")
    if references:
        parts.append(f"References: {references}")
    return " ".join(part for part in parts if part)


def _category_from_message(message: str) -> str:
    lower = message.lower()
    if "header" in lower or "clickjacking" in lower or "content-security-policy" in lower:
        return "Security Headers"
    if "cookie" in lower:
        return "Cookie Security"
    if "method" in lower or "options" in lower:
        return "HTTP Methods"
    if "directory" in lower or "file" in lower or "path" in lower:
        return "Exposed Resource"
    if "server" in lower or "version" in lower or "banner" in lower:
        return "Information Disclosure"
    return "Web Vulnerability"


def _severity_from_message(message: str) -> str:
    lower = message.lower()
    high_terms = (
        "command execution",
        "remote shell",
        "sql injection",
        "authentication bypass",
        "default credential",
        "password file",
        "config file",
        "backup file",
        "phpinfo",
        "outdated",
        "vulnerable",
        "cve-",
    )
    medium_terms = (
        "directory indexing",
        "allowed http methods",
        "x-frame-options",
        "content-security-policy",
        "strict-transport-security",
        "x-content-type-options",
        "cookie",
    )
    low_terms = ("server banner", "server leaks", "version", "powered by")

    if any(term in lower for term in high_terms):
        return "high"
    if any(term in lower for term in medium_terms):
        return "medium"
    if any(term in lower for term in low_terms):
        return "low"
    return "medium"


def _remediation_for_message(message: str) -> str:
    lower = message.lower()
    if "header" in lower or "clickjacking" in lower:
        return "Set the missing security header in the web server or application response configuration."
    if "cookie" in lower:
        return "Set secure cookie attributes such as HttpOnly, Secure, and SameSite where appropriate."
    if "directory indexing" in lower:
        return "Disable directory listing and restrict direct access to sensitive paths."
    if "method" in lower or "options" in lower:
        return "Disable unnecessary HTTP methods and restrict methods to the minimum required set."
    if "outdated" in lower or "vulnerable" in lower or "cve-" in lower:
        return "Upgrade the affected component and verify that vendor security patches are applied."
    return "Review the Nikto finding, confirm business impact, and harden the affected web server configuration."
