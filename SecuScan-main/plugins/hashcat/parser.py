from typing import Dict, List


def parse(output: str) -> Dict[str, object]:
    findings: List[Dict[str, object]] = []
    recovered: List[Dict[str, str]] = []

    for line in output.splitlines():
        text = line.strip()
        if not text or text.startswith("[") or ":" not in text:
            continue

        hash_value, password = text.split(":", 1)
        hash_value = hash_value.strip()
        password = password.strip()

        if not hash_value or not password:
            continue

        recovered.append({"hash": hash_value, "password": password})
        findings.append(
            {
                "title": "Hash Recovered",
                "category": "Password Recovery",
                "severity": "high",
                "description": f"Recovered credential for hash {hash_value}.",
                "remediation": "Force password rotation and enforce stronger password policy.",
                "metadata": {"hash": hash_value, "password": password},
            }
        )

    return {
        "findings": findings,
        "count": len(findings),
        "recovered": recovered,
    }
