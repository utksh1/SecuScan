# Plugin Reviewer Rubric

This document serves as the guide and checklist for maintainers and reviewers evaluating new or modified SecuScan plugins. It defines the validation steps, security audit rules, and compliance criteria that must be met before a plugin PR is merged.

---

## Pre-merge Gate Checklist

Reviewers must go through the following validation checks for every plugin PR:

- [ ] **Validation Script Execution**:
  Verify that the single-plugin validation script exits successfully:
  ```bash
  python scripts/validate_plugin.py --plugin <plugin_id>
  ```
- [ ] **Checksum Match**:
  Ensure the `checksum` in `metadata.json` is correct and matches the computed files' hash. Run the following to confirm no modifications were made after signing:
  ```bash
  python scripts/refresh_plugin_checksum.py --plugin <plugin_id> --dry-run
  ```
  *(The output must say: `[OK] <plugin_id> — checksum already up to date`)*
- [ ] **Risk and Safety Classification**:
  Review the configured `safety.level` against the actual scanning impact:
  - `safe`: Only passive collection, offline static analysis, or standard low-impact queries (e.g. `ping`).
  - `intrusive`: Active port scans, brute-force engines, web directory fuzzing, or crawlers that generate significant target traffic.
  - `exploit`: CVE validation scripts, state-changing payloads, or active compromise attempts.
  - *Verify: If `safety.requires_consent` is true, ensure `safety.consent_message` explains the specific risks clearly to operators.*
- [ ] **Parser Security Scan**:
  For custom parsers (`parser.py`), review the code line-by-line or run a quick grep search to ensure no forbidden functions or libraries are used:
  ```bash
  grep -Ei "exec|eval|os\.system|subprocess|environ|socket|urllib|requests|secuscan" plugins/<plugin_id>/parser.py
  ```
  *(Ensure all matches are benign comments or import/variable declarations, and do not call system shells or external endpoints).*
- [ ] **Dependency Alignment**:
  - For CLI plugins, ensure `engine.binary` is declared inside `dependencies.binaries`.
  - For Python custom parsers, ensure any external library (outside standard python text libraries) is declared under `dependencies.python_packages`.

---

## Accepted Pattern Examples

### Acceptable Metadata (`metadata.json`)

```json
{
  "id": "whois_lookup",
  "name": "WHOIS Lookup",
  "description": "Retrieve domain registration and owner details.",
  "version": "1.0.0",
  "category": "recon",
  "icon": "globe",
  "engine": {
    "type": "cli",
    "binary": "whois"
  },
  "command_template": [
    "whois",
    "{target}"
  ],
  "fields": [
    {
      "id": "target",
      "label": "Domain Target",
      "type": "text",
      "required": true,
      "help": "Target domain name to query WHOIS records for"
    }
  ],
  "output": {
    "parser": "custom"
  },
  "safety": {
    "level": "safe",
    "requires_consent": false
  },
  "dependencies": {
    "binaries": [
      "whois"
    ]
  },
  "checksum": "19b48b61c5a9bbf6f5bf1b714b714b714b714b714b714b714b714b714b714b71"
}
```

### Acceptable Parser (`parser.py`)

```python
import re

def parse(output: str) -> dict:
    findings = []

    # Process text deterministically using standard libraries
    for line in output.splitlines():
        if line.startswith("Registrar:"):
            findings.append({
                "registrar": line.split(":", 1)[1].strip(),
                "type": "info"
            })

    return {"findings": findings}
```

---

## Rejected Pattern Examples

### Rejected Metadata (`metadata.json`)

```json
{
  "id": "unsafe_port_scanner",
  "name": "Aggressive Scanner",
  "description": "Performs intensive vulnerability checks.",
  "version": "1.0.0",
  "category": "recon",
  "icon": "scan",
  "engine": {
    "type": "cli",
    "binary": "nmap"
  },
  "command_template": [
    "nmap",
    "-T4",
    "-A",
    "{target}"
  ],
  "fields": [
    {
      "id": "target",
      "label": "Target IP",
      "type": "string"
      // REJECTED: Missing "help" text on fields triggers validation warnings.
    }
  ],
  "output": {
    "parser": "text"
  },
  "safety": {
    "level": "safe", // REJECTED: Aggressive active nmap scans must be marked "intrusive".
    "requires_consent": true
    // REJECTED: Requires consent but "consent_message" is missing.
  },
  // REJECTED: Missing "dependencies" block listing nmap binary.
  "checksum": "1234" // REJECTED: Invalid checksum length (must be a 64-char hex string).
}
```

### Rejected Parser (`parser.py`)

```python
import os
import socket
import sys

# REJECTED: Importing forbidden internal packages
import secuscan.config

def parse(output: str) -> dict:
    # REJECTED: Forbidden exec() usage runs arbitrary code
    exec("print('dangerous execution')")

    # REJECTED: Spawning system shell processes
    os.system("rm -rf /tmp/data")

    # REJECTED: Interacting with the network
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(("evil-malicious-site.com", 80))

    # REJECTED: Writing files to filesystem
    with open("results.txt", "w") as f:
        f.write(output)

    # REJECTED: Accessing sensitive application environment variables
    db_password = os.environ.get("DATABASE_URL")

    return {"findings": []}
```

---

## Reference Guides

- [Plugin Security Checklist](plugin-security-checklist.md)
- [Plugin Field Validation](../plugin-validation.md)
