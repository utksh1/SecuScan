# Plugin Security Checklist

This document describes the security requirements and validation criteria for all SecuScan plugins. To ensure the integrity of the scanning platform and protect the host systems running SecuScan, all plugin contributions must adhere strictly to these guidelines.

---

## Forbidden Patterns in `parser.py`

Custom parsers run inside a subprocess execution boundary to minimize impact on the core backend. However, to prevent Remote Code Execution (RCE), data extraction, or side-effects, the following behaviors are strictly forbidden in `parser.py`:

*   **No Dynamic Code Execution**: Do not use `exec`, `eval`, `compile`, or any dynamic code execution functions.
*   **No System / Subprocess Invocation**: Do not import or call `os.system`, `subprocess.*`, `pty`, or any other shell-execution or process-spawning utilities.
*   **No Secret or Environment Reads**: Do not read from `os.environ`. The sandbox strips application secrets (e.g. `SECUSCAN_VAULT_KEY`, database credentials, API keys) from the environment of the child process. Reading from them is a security red flag and will fail review.
*   **No File System Writes**: Do not write to, modify, or delete any files. Parsers must be read-only on input data.
*   **No Network Access**: Do not import or use `socket`, `urllib`, `requests`, `http.client`, or any other network libraries. Parsers must run offline, without network access.
*   **No Internal Backend Imports**: Do not import from the `secuscan.*` package. The parser must remain isolated and self-contained.

---

## Safe Parser Rules

For custom parsers (`parser.py`), the execution environment enforces a strict contract:

1.  **Required Interface**:
    The parser must define a callable function named `parse`:
    ```python
    def parse(output: str) -> dict:
        # Implementation
        return {"findings": [...]}
    ```
2.  **Allowed Imports**:
    Only standard library text/json processing modules are safe to import:
    *   `re` (Regular expressions)
    *   `json` (JSON parsing)
    *   `datetime` (Time/date parsing)
    *   `math`, `string` (Basic math/string utilities)
3.  **Determinism**:
    The parser must be completely deterministic and side-effect free. Given the same input, it must always return the exact same output dictionary without modifying external state.

### Examples

#### [OK] Accepted Parser Pattern
```python
import json
import re

def parse(output: str) -> dict:
    findings = []
    # Parse output safely using regex
    for line in output.splitlines():
        match = re.search(r"VULN: (\w+) - Severity: (\w+)", line)
        if match:
            findings.append({
                "title": match.group(1),
                "severity": match.group(2).lower()
            })
    return {"findings": findings}
```

#### [REJECTED] Forbidden Parser Pattern
```python
import os
import subprocess

# FORBIDDEN: Shell execution & exec
def parse(output: str) -> dict:
    # This will raise an error at run time/review time
    os.system("echo 'executing malicious command'")
    exec("print('arbitrary code run')")

    # FORBIDDEN: Accessing system environment variables
    secret_key = os.environ.get("SECUSCAN_VAULT_KEY")

    # FORBIDDEN: Writing files
    with open("/tmp/output.txt", "w") as f:
        f.write(output)

    return {"findings": []}
```

---

## Metadata Requirements

Plugin metadata defined in `metadata.json` must pass strict schema validation against `REQUIRED_TOP_LEVEL_FIELDS` defined in `plugin_validator.py`.

### Required Schema Fields

Every plugin must define the following fields in its `metadata.json`:

| Field | Type | Allowed Values / Pattern | Description |
|---|---|---|---|
| `id` | String | Alphanumeric & underscores | A unique, lowercase identifier matching the folder name. |
| `name` | String | Text | User-friendly name of the plugin. |
| `description`| String | Text | A brief explanation of what the plugin does. |
| `version` | String | SemVer (e.g. `1.0.0`) | Version of the plugin. |
| `category` | String | One of the recognized categories | Must be one of: `recon`, `vulnerability`, `web`, `exploit`, `network`, `expert`, `code`, `forensics`, `utils`, `execution`, `security`, `robots`. |
| `icon` | String | Icon name | UI icon associated with the plugin (e.g., `ping`, `search`). |
| `engine` | Object | `{ "type": "cli"\|"python"\|"docker", ... }` | Execution configuration: `cli` requires `binary`; `docker` requires `image`. |
| `command_template` | List | String tokens with placeholders | CLI parameters to build the scan command (e.g. `["ping", "-c", "{count}", "{target}"]`). Placeholders must map to declared fields. |
| `fields` | List | Field objects | Form fields for user input. Each field must have `id`, `label`, `type` (e.g. `string`, `integer`, `text`), and `help` text. |
| `output` | Object | `{ "parser": "json"\|"text"\|"custom"\|"none" }` | Output handling strategy. Setting `custom` requires a `parser.py` file. |
| `safety` | Object | `{ "level": "safe"\|"intrusive"\|"exploit", "requires_consent": bool }` | Risk classification. If `requires_consent` is `true`, a non-empty `consent_message` is mandatory. |
| `checksum` | String | 64-character SHA-256 hex string | Integrity verification digest of the plugin files. |

> [!IMPORTANT]
> If `safety.requires_consent` is set to `true`, the `consent_message` field must be populated with a warning message shown to the user before they can execute the scan.
> Missing user-facing `help` text on fields under `fields[*].help` triggers validation warnings during automated checks.

---

## Dependency Declaration

To ensure plugins resolve correct system/runtime environments:

1.  **System Binaries**:
    CLI plugins must declare the binaries they depend on under `dependencies.binaries`.
    ```json
    "dependencies": {
      "binaries": ["nmap", "curl"]
    }
    ```
2.  **Python Packages**:
    Custom Python parser dependencies must be declared under `dependencies.python_packages`.
    ```json
    "dependencies": {
      "python_packages": ["beautifulsoup4"]
    }
    ```

---

## Signing & Checksum Workflow

Every time you modify `metadata.json` or `parser.py`, you must refresh the integrity checksum before committing. If the checksum is incorrect or missing, the backend loader will reject the plugin.

### Local Checksum Regeneration

Run the following helper script from the repository root:

```bash
# Refresh a single plugin by its folder name (plugin id)
python scripts/refresh_plugin_checksum.py --plugin <plugin_id>

# Refresh all plugins at once
python scripts/refresh_plugin_checksum.py --all
```

### HMAC Signatures (Maintainer/Operator Enforcement)

In production or strict execution environments, plugins can be cryptographically signed using an HMAC signature to prevent tampered code from executing:

```bash
# Sign all plugins with a secret signature key
python scripts/sign_plugins.py --plugins-dir plugins --signature-key $SECUSCAN_PLUGIN_KEY
```

To enable enforcement on the backend, set:
```env
enforce_plugin_signatures=true
```
In the `.env` configuration file. If enabled, any unsigned or improperly signed plugin will fail integrity checks at startup and immediately before execution.

### Digest Algorithm Details

The backend verifies integrity by computing a combined SHA-256 digest:
1.  Strip mutable fields (`checksum` and `signature`) from `metadata.json`.
2.  Serialize the remaining fields into canonical JSON (sorted keys, no extra whitespace) and compute the SHA-256 hex digest.
3.  Read `parser.py`, normalize line endings (replace CRLF `\r\n` with LF `\n` to prevent platform mismatches), and compute the SHA-256 hex digest.
4.  Combine them as `sha256(metadata_digest:parser_digest)` to form the final `checksum` value.

This calculation is implemented in `PluginManager.compute_plugin_digest`.

---

## Local Verification

Before submitting a Pull Request, verify your plugin metadata and parser structure locally:

```bash
python scripts/validate_plugin.py --plugin <plugin_id>
```

This verifies schema validity, checks that the checksum is present and correct, and ensures the parser imports cleanly.
