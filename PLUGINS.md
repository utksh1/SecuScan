# SecuScan Plugin Catalogue

This file is a human-readable index of the plugins currently present in `plugins/*/metadata.json`.

Last synced: 2026-05-11

## At a Glance

- Total plugins: 60
- Safe plugins: 27
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
| `recon` | 19 |
| `vulnerability` | 12 |
| `robots` | 5 |
| `web` | 5 |
| `exploit` | 5 |
| `network` | 3 |
| `expert` | 3 |
| `code` | 2 |
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
| Crawler | `crawler` | `robots` | `intrusive` | `katana` | Recursive web crawler for link discovery. |
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
| httpx | `httpx` | `recon` | `safe` | `httpx` | Live host probing with status, title, and technology fingerprinting. |
| IaC Scanner (Checkov) | `iac_scanner` | `vulnerability` | `safe` | `python3` | Analyze Terraform and CloudFormation code for flaws. |
| ICMP Ping | `icmp_ping` | `utils` | `safe` | `ping` | Check if a server is live and responds to ICMP Echo requests. |
| Joomla Security Scan | `joomscan` | `vulnerability` | `intrusive` | `joomscan` | Joomla security scanner for version and common weakness discovery. |
| Katana | `katana` | `recon` | `intrusive` | `katana` | Web crawling for endpoint and route discovery. |
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
| Sharepoint Scanner | `sharepoint_scanner` | `vulnerability` | `intrusive` | `nuclei` | Check SharePoint for security issues, misconfigs, and more. |
| Sitemap Generator | `sitemap_gen` | `robots` | `intrusive` | `katana` | Build complete XML sitemaps by autonomously parsing targets. |
| Sniper: Auto-Exploiter | `sniper` | `exploit` | `exploit` | `python3` | Validate critical CVEs by automatic exploitation. |
| Spider | `spider` | `robots` | `intrusive` | `katana` | Advanced web spider with JS execution support. |
| SQL Injection Feasibility | `sqli_checker` | `expert` | `intrusive` | `ghauri` | SQL injection feasibility scanner powered by Ghauri. |
| SQLi Exploiter | `sqli_exploiter` | `exploit` | `exploit` | `sqlmap` | Exploit SQL injection in web apps to extract data. |
| SQL Injection Testing | `sqlmap` | `web` | `exploit` | `sqlmap` | Automatic SQL injection and database takeover tool. |
| SSH Runner | `ssh_runner` | `execution` | `intrusive` | `ssh` | Remote command execution via SSH. |
| Subdomain Finder | `subdomain-finder` | `recon` | `safe` | `subfinder` | Discover subdomains of a domain. |
| Subdomain Scanner | `subdomain_discovery` | `recon` | `safe` | `subfinder` | Enumerate subdomains using passive sources. |
| Subdomain Takeover | `subdomain_takeover` | `exploit` | `intrusive` | `subfinder` | Discover dangling DNS entries pointing to external services. |
| Subfinder | `subfinder` | `recon` | `safe` | `subfinder` | Fast passive subdomain enumeration. |
| theHarvester | `theharvester` | `recon` | `safe` | `theHarvester` | OSINT collection for emails, domains, and hosts. |
| TLS Security Analysis | `tls_inspector` | `security` | `safe` | `openssl` | Examine TLS/SSL certificates and cipher configurations. |
| Uncover | `uncover` | `recon` | `safe` | `uncover` | Discover internet-exposed assets from external search sources. |
| URL Fuzzer | `url-fuzzer-2` | `recon` | `intrusive` | `ffuf` | Discover hidden files and directories. |
| urlfinder | `urlfinder` | `recon` | `safe` | `urlfinder` | Passive historical URL collection. |
| Virtual Hosts Finder | `virtual-host-finder` | `recon` | `intrusive` | `ffuf` | Find multiple websites hosted on the same server. |
| Volatility | `volatility` | `forensics` | `intrusive` | `volatility3` | Memory forensics workflow using Volatility 3 plugins. |
| WAF Detector | `waf-detection` | `recon` | `safe` | `wafw00f` | Fingerprint the Web Application Firewall behind target app. |
| WAF Detector | `waf_detector` | `robots` | `safe` | `wafw00f` | Automatically identify Web Application Firewalls protecting targets. |
| Website Recon | `website-recon-2` | `recon` | `safe` | `httpx` | Fingerprint web technologies of target website. |
| Domain Registration Lookup | `whois_lookup` | `utils` | `safe` | `python3` | Domain registration information lookup. |
| WordPress Security Scan | `wpscan` | `vulnerability` | `intrusive` | `wpscan` | WordPress security scanner for plugin, theme, and core risk visibility. |
| XSS Exploiter | `xss_exploiter` | `exploit` | `exploit` | `python3` | Exploit XSS in real-life attacks to extract cookies and data. |
| Binary Signature Scan | `yara_scan` | `forensics` | `intrusive` | `yara` | Binary and file-system signature matching with YARA rules. |
| DAST Web Proxy (ZAP) | `zap_scanner` | `vulnerability` | `exploit` | `python3` | Dynamic proxy spidering and payload injection. |

## Examples for common field types in metadata.json

## string - Single-line text

-Use for free-form text inputs such as hostnames, domain names, file paths, or any
value that does not fit a more specific type.

```json
{
  "id": "target",
  "label": "Root Domain",
  "type": "string",
  "required": true,
  "placeholder": "example.com",
  //"description": "The root domain to enumerate. Do not include a scheme or trailing slash."
}
```

## url - URL

-Use when the field expects a well-formed URL (a complete target url).

```json
{
  "id": "target_url",
  "label": "Target URL",
  "type": "url",
  "required": true,
  "placeholder": "https://example.com",
  //"description": "Full URL of the target, including scheme. Must begin with http:// or https://."
}
```

## select - Single-choice dropdown

- Use when user must choose a predefined option or say exactly one value from a fixed list.

```json
{
  "id": "scan_depth",
  "label": "Scan Depth",
  "type": "select",
  "required": true,
  "options": ["shallow", "normal", "deep"],
  "default": "normal",
  //"description": "Controls how aggressively the plugin probes the target. Start with 'normal' for most scans."
}
```












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
