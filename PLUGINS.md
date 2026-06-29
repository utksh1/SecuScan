# SecuScan Plugin Catalogue

## Plugin Development

New contributors should refer to these resources:
- [Plugin Development Walkthrough](docs/plugins/plugin-development-walkthrough.md)
- [Plugin Security Checklist & Guidelines](docs/plugins/plugin-security-checklist.md)
- [Plugin Reviewer Rubric](docs/plugins/plugin-reviewer-rubric.md)

This file is a human-readable index of the plugins currently present in `plugins/*/metadata.json`.

Last synced: 2026-05-11

## At a Glance

- Total plugins: 59
- Safe plugins: 26
- Intrusive plugins: 25
- Exploit plugins: 8
- Source of truth: each plugin's `metadata.json`

## Safety Levels

| Level | Meaning |
| --- | --- |
| `safe` | Passive or low-impact discovery that is less likely to modify target state. |
| `intrusive` | Active probing, crawling, brute-force checks, or remote interaction that can generate noticeable traffic. |
| `exploit` | Validation or exploitation workflows that can extract data, change state, or create higher operational risk. |

Only run scans against systems you own or are explicitly authorized to assess.

## Category Summary

| Category | Count |
| --- | ---: |
| `recon` | 17 |
| `vulnerability` | 12 |
| `robots` | 5 |
| `web` | 5 |
| `exploit` | 5 |
| `network` | 3 |
| `expert` | 3 |
| `code` | 3 |
| `forensics` | 2 |
| `utils` | 2 |
| `execution` | 1 |
| `security` | 1 |

## Plugin Index

| Plugin | ID | Category | Safety | Primary Binary | Summary |
| --- | --- | --- | --- | --- | --- |
| Amass | `amass` | `recon` | `safe` | `amass` | Deep attack-surface mapping and subdomain discovery. |
| API Scanner | `api_scanner` | `vulnerability` | `intrusive` | `nuclei` | Check for specific API vulnerabilities (REST and GraphQL). |
| Cloud Scanner | `cloud_scanner` | `vulnerability` | `intrusive` | `python3` | Cloud infrastructure security (AWS/GCP/Azure). |
| S3 / Blob Auditor | `cloud_storage_auditor` | `vulnerability` | `safe` | `uncover` | Find misconfigured S3 buckets and exposed cloud storage. |
| Code Analyzer (Bandit) | `code_analyzer` | `code` | `safe` | `bandit` | Static analysis for Python code. |
| Container Scan (Trivy) | `container_scanner` | `network` | `safe` | `trivy` | Scan Docker images and registries for known vulnerabilities. |
| Crawler | `crawler` | `robots` | `intrusive` | `katana` | Depth-limited Katana crawl for recursive link discovery. |
| Directory Discovery | `dir_discovery` | `web` | `intrusive` | `ffuf` | Discover hidden directories and files on web servers. |
| DNS Reconnaissance | `dns_enum` | `recon` | `safe` | `dnsrecon` | Enumerate DNS records and configurations. |
| dnsx | `dnsx` | `recon` | `safe` | `dnsx` | DNS resolution and wildcard-aware validation at scale. |
| Domain Finder | `domain-finder` | `recon` | `safe` | `amass` | Discover additional domain names of target organization. |
| Drupal Security Scan | `droopescan` | `vulnerability` | `intrusive` | `droopescan` | Drupal-focused CMS scanner for version and surface enumeration. |
| Payload Fuzzer | `fuzzer` | `robots` | `exploit` | `python3` | Autonomously fuzz target fields with massive dictionaries. |
| Google Hacking | `google-dorking` | `recon` | `safe` | `python3` | Find publicly indexed information about target. |
| Password Recovery Audit | `hashcat` | `expert` | `exploit` | `hashcat` | Password recovery and hash audit workflow. |
| HTTP Inspector | `http_inspector` | `web` | `safe` | `curl` | Inspect HTTP/HTTPS endpoints for headers, cookies, and TLS configuration. |
| HTTP Request Logger | `http_request_logger` | `exploit` | `intrusive` | `httpx` | Handle incoming HTTP requests and record data. |
| httpx | `httpx` | `recon` | `safe` | `httpx` | Probe live hosts and collect reachability information, status codes, page titles, and basic technology indicators. |
| IaC Scanner (Checkov) | `iac_scanner` | `vulnerability` | `safe` | `python3` | Analyze Terraform and CloudFormation code for flaws. |
| ICMP Ping | `icmp_ping` | `utils` | `safe` | `ping` | Check if a server is live and responds to ICMP Echo requests. |
| Joomla Security Scan | `joomscan` | `vulnerability` | `intrusive` | `joomscan` | Joomla security scanner for version and common weakness discovery. |
| Katana | `katana` | `recon` | `intrusive` | `katana` | Baseline Katana URL discovery using the default crawl behavior. |
| K8s Scanner | `kubernetes_scanner` | `vulnerability` | `intrusive` | `python3` | Kubernetes cluster security assessment. |
| Exploitation Connector | `metasploit` | `expert` | `exploit` | `msfconsole` | Metasploit connector for controlled exploit-module execution. |
| Network Scanner | `network_scanner` | `vulnerability` | `intrusive` | `nmap` | Check for 10,000+ CVEs and server misconfigurations. |
| Nikto | `nikto` | `web` | `intrusive` | `nikto` | Web server vulnerability scanner powered by the Nikto CLI. |
| Network Scanning | `nmap` | `network` | `safe` | `nmap` | Network discovery and port scanning tool. |
| Template Vulnerability Scan | `nuclei` | `web` | `intrusive` | `nuclei` | Fast and customizable vulnerability scanner. |
| Password Auditor | `password_auditor` | `vulnerability` | `intrusive` | `python3` | Discover weak credentials in network services and web apps. |
| People Hunter | `people-email-discovery` | `recon` | `safe` | `theHarvester` | Discover email addresses and social media profiles. |
| Port Scanner | `port-scanner` | `recon` | `intrusive` | `nmap` | Detect open ports and fingerprint services. |
| Advanced Network Recon | `scapy_recon` | `network` | `safe` | `python3` | Advanced network probing using Scapy. |
| Secret Scanner | `secret_scanner` | `code` | `safe` | `gitleaks` | Scan directories for hardcoded secrets. |
| Semgrep Scanner | `semgrep_scanner` | `code` | `safe` | `semgrep` | Multi-language static code analysis using Semgrep. |
| Sharepoint Scanner | `sharepoint_scanner` | `vulnerability` | `intrusive` | `nuclei` | Check SharePoint for security issues, misconfigs, and more. |
| Sitemap Generator | `sitemap_gen` | `robots` | `intrusive` | `katana` | Depth-focused Katana crawl for sitemap-style URL inventory. |
| Sniper: Auto-Exploiter | `sniper` | `exploit` | `exploit` | `python3` | Validate critical CVEs by automatic exploitation. |
| Spider | `spider` | `robots` | `intrusive` | `katana` | JavaScript-aware Katana spider for deeper client-side route discovery. |
| SQL Injection Feasibility | `sqli_checker` | `expert` | `intrusive` | `ghauri` | Validates potential SQL injection vulnerabilities without exploitation. |
| SQLi Exploiter | `sqli_exploiter` | `exploit` | `exploit` | `sqlmap` | Exploitation-focused workflow for data extraction from confirmed SQL injection findings. |
| SQL Injection Testing | `sqlmap` | `web` | `exploit` | `sqlmap` | Detects SQL injection vulnerabilities and supports controlled database enumeration. |
| SSH Runner | `ssh_runner` | `execution` | `intrusive` | `ssh` | Remote command execution via SSH. |
| Subdomain Discovery (Configurable) | `subdomain_discovery` | `recon` | `safe` | `subfinder` | Comprehensive configurable subdomain enumeration via passive sources. Thread count and source coverage tunable via presets. |
| Subdomain Takeover | `subdomain_takeover` | `exploit` | `intrusive` | `subfinder` | Discover dangling DNS entries pointing to external services. |
| Subfinder (Quick) | `subfinder` | `recon` | `safe` | `subfinder` | Quick passive subdomain enumeration with minimal configuration — just provide a root domain. |
| theHarvester | `theharvester` | `recon` | `safe` | `theHarvester` | OSINT collection for emails, domains, and hosts. |
| TLS Security Analysis | `tls_inspector` | `security` | `safe` | `openssl` | Examine TLS/SSL certificates and cipher configurations. |
| Uncover | `uncover` | `recon` | `safe` | `uncover` | Discover internet-exposed assets from external search sources. |
| URL Fuzzer | `url-fuzzer-2` | `recon` | `intrusive` | `ffuf` | Discover hidden files and directories. |
| urlfinder | `urlfinder` | `recon` | `safe` | `urlfinder` | Passive historical URL collection. |
| Virtual Hosts Finder | `virtual-host-finder` | `recon` | `intrusive` | `ffuf` | Find multiple websites hosted on the same server. |
| Volatility | `volatility` | `forensics` | `intrusive` | `volatility3` | Memory forensics workflow using Volatility 3 plugins. |
| WAF Detector | `waf_detector` | `robots` | `safe` | `wafw00f` | Automatically identify Web Application Firewalls protecting targets. |
| Website Recon | `website-recon-2` | `recon` | `safe` | `httpx` | Perform website reconnaissance focused on identifying web technologies, frameworks, and application stack details. |
| Domain Registration Lookup | `whois_lookup` | `utils` | `safe` | `python3` | Domain registration information lookup. |
| WordPress Security Scan | `wpscan` | `vulnerability` | `intrusive` | `wpscan` | WordPress security scanner for plugin, theme, and core risk visibility. |
| XSS Exploiter | `xss_exploiter` | `exploit` | `exploit` | `python3` | Exploit XSS in real-life attacks to extract cookies and data. |
| Binary Signature Scan | `yara_scan` | `forensics` | `intrusive` | `yara` | Binary and file-system signature matching with YARA rules. |
| DAST Web Proxy (ZAP) | `zap_scanner` | `vulnerability` | `exploit` | `python3` | Dynamic proxy spidering and payload injection. |

### Hashcat Output Artifacts

- Session files for resumable runs
- Potfile entries containing recovered hashes
- Recovered credential output returned by the parser

Review and remove these artifacts after authorized assessments.

### SQL Injection Plugin Guidance

- `sqli_checker` should be used to validate whether a target appears vulnerable to SQL injection and to assess feasibility before exploitation.
- `sqlmap` should be used for SQL injection testing and controlled database enumeration during assessment workflows.
- `sqli_exploiter` should be used only after a vulnerability has been confirmed and exploitation or data extraction is required.

## Plugin Input Schema with Examples

Plugins can tell us about configurable user inputs through schema fields in their
`metadata.json`.

### Supported Field Types

Example schema:

```json
{
  "fields": [
    {
      "id": "target",
      "label": "Target URL",
      "type": "string",
      "required": true,
      "placeholder": "https://example.com",
      "help": "Full URL of the target including scheme.",
      "validation": {
        "validation_type": "url",
        "message": "Enter a valid URL starting with http:// or https://"
      }
    },
    {
      "id": "scan_type",
      "label": "Scan Type",
      "type": "select",
      "required": true,
      "options": [
        { "value": "quick", "label": "Quick" },
        { "value": "full",  "label": "Full"  }
      ]
    },
    {
      "id": "checks",
      "label": "Checks",
      "type": "multiselect",
      "required": false,
      "options": [
        { "value": "headers", "label": "Headers" },
        { "value": "ssl",     "label": "SSL"     },
        { "value": "cookies", "label": "Cookies" }
      ]
    },
    {
      "id": "recursive",
      "label": "Enable Recursive Scan",
      "type": "boolean",
      "required": false,
      "default": false
    },
    {
      "id": "timeout",
      "label": "Timeout (seconds)",
      "type": "integer",
      "required": false,
      "default": 30,
      "validation": {
        "min": 1,
        "max": 3600
      }
    },
    {
      "id": "wordlist_path",
      "label": "Wordlist Path",
      "type": "path",
      "required": false
    }
  ]
}
```

### Field Types

| Type Value | Input Rendered | Notes |
| --- | --- | --- |
| `string` | Text input | Use `validation.validation_type` for URL, hostname, IP, etc. |
| `integer` | Number input | Use `validation.min` / `validation.max` for range |
| `boolean` | Toggle / checkbox | `default` should be `true` or `false` |
| `select` | Dropdown (single) | `options` must be `[{ "value": ..., "label": ... }]` |
| `multiselect` | Checkbox group | Same options shape as `select` |
| `path` | File-path text input | No validation block needed |

For the full list of named validation presets (e.g. `url`, `hostname`, `domain`, `ipv4`, `port`, `cidr`) and range rules, see [plugin-validation.md](docs/plugin-validation.md).

### Required vs Optional Fields

- `"required": true` means that the user must provide a value before running the plugin.
- `"required": false` means that the field is optional.
- Optional fields may define a `"default"` value.

### Preset Mapping

Plugin presets shall map directly to schema keys.

Example presets:

```json
{
  "presets": {
    "quick": {
      "target": "https://example.com",
      "scan_type": "quick",
      "recursive": false,
      "timeout": 30
    },
    "thorough": {
      "scan_type": "full",
      "recursive": true,
      "timeout": 300
    }
  }
}
```

Each preset key shall exactly match a corresponding field `"id"` value.

## Maintenance Notes

- If a plugin is added, renamed, or removed, update this file from the plugin metadata rather than editing counts by hand.
- Prefer keeping `id`, category, safety level, and dependency names aligned with each plugin's `metadata.json`.
## Checksum Maintenance

Plugin metadata files include integrity checksums. If you edit a plugin's
`metadata.json` or `parser.py`, you must refresh the checksum before committing
or the backend will reject the plugin during load and unrelated backend tests
will fail.

Use the helper script to refresh checksums:

```bash
# Refresh a single plugin after editing it
python scripts/refresh_plugin_checksum.py --plugin <plugin-id>

# Example
python scripts/refresh_plugin_checksum.py --plugin nmap

# Refresh all plugins at once
python scripts/refresh_plugin_checksum.py --all

# Preview what would change without writing anything
python scripts/refresh_plugin_checksum.py --all --dry-run
```

Run this script any time you:
- Edit a plugin's `metadata.json` fields
- Edit a plugin's `parser.py`
- Add a new plugin

After refreshing, run the backend tests to confirm the plugin loads correctly:

```bash
cd backend && python -m pytest
```

## Parser Integrity Enforcement

When `enforce_parser_integrity` is enabled (default: `True`), the backend
re-verifies the parser checksum immediately before executing any plugin's
`parser.py` at scan time. This closes the TOCTOU window between startup
validation and code execution by confirming the file has not been tampered
with since the plugin was loaded.

If the checksum does not match, the scan is aborted with a security error.
Set `SECUSCAN_ENFORCE_PARSER_INTEGRITY=false` in your environment to disable
this check (not recommended for production deployments).

The `parser_hash_algorithm` setting (`sha256` by default) is reserved for
future hash algorithm upgrades and is not used by the current implementation.

### Example 1 — Refresh a single plugin after editing its files

Run this after editing `plugins/nmap/metadata.json` or `plugins/nmap/parser.py`:

```bash
python scripts/refresh_plugin_checksum.py --plugin nmap
```

When the checksum is already up to date, the script reports the plugin as
`[OK]` and exits cleanly with no files modified.

When the checksum is outdated, the script prints the old and new digest values,
writes the updated checksum back into `metadata.json`, and confirms the update.

### Example 2 — Preview all plugins without writing anything (dry run)

Run this to check which plugins are out of date before committing:

```bash
python scripts/refresh_plugin_checksum.py --all --dry-run
```

In dry-run mode no files are modified. Each plugin reports either `[OK]` if
its checksum is current, or `[UPDATE]` showing what would change. A clean
state means every plugin reports `[OK]` and the final line shows zero failures.

If any `[UPDATE]` lines appear, run the same command without `--dry-run` to
apply the changes before committing.

## Plugin Validation

Validate a single plugin without loading all plugins:

```bash
# Validate by plugin id
python scripts/validate_plugin.py --plugin <plugin-id>

# Example
python scripts/validate_plugin.py --plugin nmap

# Or pass a path to the plugin directory
python scripts/validate_plugin.py --plugin plugins/nmap
```

The validation checks metadata JSON, required fields, checksums, and custom
parser imports when applicable.

### Metadata quality lint rules

Two additional lint checks help maintain high-quality plugin metadata:

1. **Missing field help text** — Each field in the `fields` array should include
   a `help` string that provides a brief user-facing description of the input.
   Fields without `help` text produce a lint **warning** (the plugin is still valid).

   ```json
   // Good — has help text
   { "id": "target", "label": "Target", "type": "text", "help": "IP address or hostname to scan" }

   // Bad — missing help text (lint warning)
   { "id": "target", "label": "Target", "type": "text" }
   ```

2. **Ambiguous category** — Each plugin's `category` must be one of the
   recognized categories: `recon`, `vulnerability`, `web`, `exploit`, `network`,
   `expert`, `code`, `forensics`, `utils`, `execution`, `security`, `robots`.
   Unknown or misspelled categories cause a validation **error** and block
   the plugin from being loaded.

   ```bash
   # Run the linter
   python scripts/validate_plugins.py
   ```

Existing plugins can be brought into compliance incrementally — the help
text check is a non-blocking warning, and unknown categories cause a
clear error message identifying the problem.

---

---

## Catalog Validation (For Contributors)

To prevent the index, categories, and metrics in this file from drifting out of sync with the live plugin directories, a validation tool is provided.

Before submitting a Pull Request that adds, removes, or modifies a plugin, ensure the catalog is synced by running:

```bash
python scripts/validate_plugins_catalog.py
