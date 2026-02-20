# SecuScan Plugin Directory

> **14 Plugins** across 3 safety tiers — Last synced: 2026-03-25

---

## Network Reconnaissance

### 1. 🔍 Nmap — Network Discovery & Port Scanning
**ID:** `nmap` · **Safety:** Safe · **File:** `plugins/nmap/metadata.json`

- **Presets:** 5 — Quick, Top-100, Top-1000, Service Fingerprint, Comprehensive
- **Fields:** 8 — target, preset, ports, scan_type, service_detection, os_detection, timeout, safe_mode
- **Rate Limit:** 10/hr, max 2 concurrent
- **Dependency:** `nmap`

| Preset | Ports | Timing | Risk |
|--------|-------|--------|------|
| Quick | Top 100 | T3 | Low |
| Top 100 | Top 100 (safe) | T3 | Low |
| Top 1000 | Top 1000 + sV | T3 | Low |
| Service Fingerprint | Top 1000 + sV/sC | T4 | Medium |
| Comprehensive | Full range + OS | T4 | High ⚠️ |

---

### 2. 🌍 Subdomain Discovery — Passive Enumeration
**ID:** `subdomain_discovery` · **Safety:** Safe · **File:** `plugins/subdomain_discovery/metadata.json`

- **Presets:** 2 — Quick, Comprehensive
- **Fields:** 2 — target, sources
- **Rate Limit:** 20/hr, max 1 concurrent
- **Dependency:** `subfinder`

**Capabilities:** Identifies subdomains using passive sources (Censys, Shodan, etc.) without direct interaction.

---

### 3. 🛰️ Scapy Recon — Advanced Network Probing
**ID:** `scapy_recon` · **Safety:** Safe · **File:** `plugins/scapy_recon/metadata.json`

- **Presets:** 2 — ARP Ping, ICMP Echo
- **Fields:** 3 — target, timeout, interface
- **Rate Limit:** 10/hr, max 1 concurrent
- **Dependency:** `scapy` (Python)

---

### 4. 🕵️ WHOIS Lookup — Domain Intelligence
**ID:** `whois_lookup` · **Safety:** Safe · **File:** `plugins/whois_lookup/metadata.json`

- **Presets:** 1 — Default
- **Fields:** 1 — target
- **Rate Limit:** 50/hr, max 2 concurrent
- **Dependency:** `whois`

---

### 5. 📦 DNS Enumeration — Record Discovery
**ID:** `dns_enum` · **Safety:** Safe · **File:** `plugins/dns_enum/metadata.json`

- **Presets:** 2 — Standard, Zone Transfer
- **Fields:** 2 — target, type
- **Rate Limit:** 30/hr, max 1 concurrent
- **Dependency:** `dnsrecon`

---

## Web Reconnaissance

### 6. 🌐 HTTP Inspector — Endpoint Analysis
**ID:** `http_inspector` · **Safety:** Safe · **File:** `plugins/http_inspector/metadata.json`

- **Presets:** 2 — Quick, Full
- **Fields:** 3 — url, follow_redirects, timeout
- **Rate Limit:** 100/hr, max 5 concurrent
- **Dependency:** `curl`

---

### 7. 🔐 TLS Inspector — Certificate & Cipher Analysis
**ID:** `tls_inspector` · **Safety:** Safe · **File:** `plugins/tls_inspector/metadata.json`

- **Presets:** 3 — Quick, Full, Custom Port
- **Fields:** 7 — host, port, hostname, show_chain, check_ciphers, check_protocols, timeout
- **Rate Limit:** 50/hr, max 3 concurrent
- **Dependency:** `openssl`

---

### 8. 📂 Dir Discovery — Hidden Path Enumeration
**ID:** `dir_discovery` · **Safety:** Intrusive · **File:** `plugins/dir_discovery/metadata.json`

- **Presets:** 3 — Quick, Standard, Deep
- **Fields:** 9 — base_url, wordlist, extensions, threads, delay_ms, match_codes, recursive, max_depth, timeout
- **Rate Limit:** 5/hr, max 1 concurrent
- **Dependency:** `ffuf`

---

## Code & System Analysis

### 9. 🔑 Secret Scanner — Credential Leak Detection
**ID:** `secret_scanner` · **Safety:** Safe · **File:** `plugins/secret_scanner/metadata.json`

- **Presets:** 2 — Local Dir, Repo History
- **Fields:** 2 — target_path, scan_history
- **Rate Limit:** 10/hr, max 1 concurrent
- **Dependency:** `gitleaks`

---

### 10. 🛡️ Code Analyzer (Bandit) — Python Static Analysis
**ID:** `code_analyzer` · **Safety:** Safe · **File:** `plugins/code_analyzer/metadata.json`

- **Presets:** 2 — Standard, Recursive
- **Fields:** 3 — target_path, recursive, confidence_level
- **Rate Limit:** 20/hr, max 2 concurrent
- **Dependency:** `bandit`

---

### 11. 💻 SSH Runner — Remote Command Execution
**ID:** `ssh_runner` · **Safety:** Intrusive · **File:** `plugins/ssh_runner/metadata.json`

- **Presets:** 2 — Check Uptime, Check Auth Log
- **Fields:** 3 — target, username, command
- **Rate Limit:** 5/hr, max 1 concurrent
- **Dependency:** `ssh`

---

## Web Vulnerability Assessment

### 12. 🔎 Nikto — Web Server Scanner
**ID:** `nikto` · **Safety:** Intrusive · **File:** `plugins/nikto/metadata.json`

- **Presets:** 3 — Passive, Standard, Active
- **Fields:** 7 — target, preset, check_categories, timeout, safe_mode, ssl_check, follow_redirects
- **Rate Limit:** 3/hr, max 1 concurrent
- **Dependencies:** `nikto`, `perl`

---

### 13. 🧬 Nuclei — Template-Based Vulnerability Scanner
**ID:** `nuclei` · **Safety:** Intrusive · **File:** `plugins/nuclei/metadata.json`

- **Presets:** 2 — Known CVEs, Full Template Scan
- **Fields:** 4 — target, preset, templates, severity
- **Rate Limit:** 10/hr, max 1 concurrent
- **Dependency:** `nuclei`

---

### 14. 💉 SQLMap — SQL Injection Testing
**ID:** `sqlmap` · **Safety:** Exploit ⚠️ · **File:** `plugins/sqlmap/metadata.json`

- **Presets:** 2 — Quick (Level 1/Risk 1), Aggressive (Level 5/Risk 3)
- **Fields:** 5 — url, preset, level, risk, dbs
- **Rate Limit:** 5/hr, max 1 concurrent
- **Dependency:** `sqlmap` (Python)

---

## Plugin Statistics

| Metric | Value |
|--------|-------|
| **Total Plugins** | 14 |
| **Safe** | 9 |
| **Intrusive** | 4 |
| **Exploit** | 1 |
| **Total Presets** | ~35 |
| **Total Fields** | ~60 |

---

## Safety Classification

```
┌────────────────────────────────────────────────────────┐
│  SAFE (9)         Read-only, passive observation       │
│  ├─ Nmap             Network Discovery                 │
│  ├─ HTTP Inspector   Endpoint Analysis                 │
│  ├─ TLS Inspector    Certificate Analysis              │
│  ├─ Subdomain Disc.  Passive Enum                      │
│  ├─ Scapy Recon      Advanced Probing                  │
│  ├─ WHOIS Lookup     Domain Intel                      │
│  ├─ DNS Enum         Record Discovery                  │
│  ├─ Secret Scanner   Leak Detection                    │
│  └─ Code Analyzer    Bandit (Python)                   │
├────────────────────────────────────────────────────────┤
│  INTRUSIVE (4)    Generates significant traffic        │
│  ├─ Dir Discovery    Hidden Path Enum                  │
│  ├─ Nikto            Active Probing                    │
│  ├─ Nuclei           Template Execution                │
│  └─ SSH Runner       Remote Execution                  │
├────────────────────────────────────────────────────────┤
│  EXPLOIT (1)      Can modify target state              │
│  └─ SQLMap           SQL Injection                     │
└────────────────────────────────────────────────────────┘
```

---

**Last Updated:** 2026-03-25  
**Status:** 14 Plugins Active (7 MVP + 7 Phase-2 Expanded)
