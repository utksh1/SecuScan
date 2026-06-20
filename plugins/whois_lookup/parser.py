import json
from typing import Any, Dict


def _coerce_text_row(value: Any) -> str:
    if value is None:
        return "Unknown"
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(cleaned) if cleaned else "Unknown"
    text = str(value).strip()
    return text or "Unknown"


def _parse_plain_text(output: str) -> Dict[str, Any]:
    detail = {
        "registrar": "Unknown",
        "organization": "N/A",
        "country": "N/A",
        "creation": "Unknown",
        "expiry": "Unknown",
        "nameservers": "N/A",
    }

    nameservers: list[str] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        normalized_key = key.strip().lower()
        normalized_value = value.strip()

        if normalized_key == "registrar":
            detail["registrar"] = normalized_value or "Unknown"
        elif normalized_key in {
            "registry expiry date",
            "registrar registration expiration date",
            "expiry date",
        }:
            detail["expiry"] = normalized_value or "Unknown"
        elif normalized_key in {"creation date", "created date", "registered on"}:
            detail["creation"] = normalized_value or "Unknown"
        elif normalized_key in {"registrant organization", "organization", "org"}:
            detail["organization"] = normalized_value or "N/A"
        elif normalized_key in {"registrant country", "country"}:
            detail["country"] = normalized_value or "N/A"
        elif normalized_key == "name server" and normalized_value:
            nameservers.append(normalized_value)

    if nameservers:
        detail["nameservers"] = ", ".join(nameservers)

    findings = [
        {
            "title": "WHOIS Record for Target",
            "category": "Domain Info",
            "severity": "info",
            "description": (
                f"Registrar: {detail['registrar']}\n"
                f"Expiry: {detail['expiry']}\n"
                f"Name Servers: {detail['nameservers']}"
            ),
            "remediation": "Review domain registration data for accuracy and privacy settings (WHOIS privacy).",
            "metadata": {"raw_output": output},
        }
    ]

    return {
        "findings": findings,
        "rows": [detail],
        "detail": detail,
    }


def parse(output: str) -> Dict[str, Any]:
    """
    Parse WHOIS output (JSON format from whois_tool.py).
    """
    try:
        # Robust JSON extraction: find the first '{' and last '}'
        start = output.find("{")
        end = output.rfind("}")
        if start != -1 and end != -1:
            json_content = output[start : end + 1]
            data = json.loads(json_content)
        else:
            data = json.loads(output)
    except Exception:
        # Older tool output and tests may provide plain-text WHOIS content.
        return _parse_plain_text(output)

    findings = []

    registrar = data.get("registrar") or data.get("registrar_name", "Unknown")
    expiry = data.get("expiration_date")
    if isinstance(expiry, list):
        expiry = expiry[0]

    nameservers = _coerce_text_row(data.get("name_servers", []))

    creation = data.get("creation_date")
    if isinstance(creation, list):
        creation = creation[0]
    # Format date string (e.g. 1997-09-15)
    creation_str = str(creation).split(" ")[0] if creation else "Unknown"
    expiry_str = str(expiry).split(" ")[0] if expiry else "Unknown"

    summary_data = {
        "registrar": registrar,
        "organization": data.get("org") or "N/A",
        "country": data.get("country") or "N/A",
        "creation": creation_str,
        "expiry": expiry_str,
        "nameservers": nameservers,
    }

    findings.append(
        {
            "title": f"WHOIS Record for {data.get('domain_name', 'Target')}",
            "category": "Domain Info",
            "severity": "info",
            "description": (
                f"Registrar: {summary_data['registrar']}\n"
                f"Expiry: {summary_data['expiry']}\n"
                f"Name Servers: {summary_data['nameservers']}"
            ),
            "remediation": "Review domain registration data for accuracy and privacy settings (WHOIS privacy).",
            "metadata": data,
        }
    )

    return {"findings": findings, "rows": [summary_data], "detail": summary_data}
