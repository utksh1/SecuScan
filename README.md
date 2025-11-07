# SecuScan — Local-First Pentesting Toolkit
## Final Detailed Product Specification, November 2025

---

**Document Version:** 1.0  
**Classification:** Internal Release  
**Target Audience:** Engineering Team, Security Researchers, Pentesting Students  
**Last Updated:** November 2, 2025  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Tool Catalogue Overview](#2-tool-catalogue-overview)
3. [UI and UX Architecture](#3-ui-and-ux-architecture)
4. [Plugin Metadata System](#4-plugin-metadata-system)
5. [Backend API Contract](#5-backend-api-contract)
6. [Standardized Output Schema](#6-standardized-output-schema)
7. [Database and Storage Layout](#7-database-and-storage-layout)
8. [Sandboxing and Security Layer](#8-sandboxing-and-security-layer)
9. [UX, Legal, and Learning Tools](#9-ux-legal-and-learning-tools)
10. [Packaging and Installation](#10-packaging-and-installation)
11. [Testing and CI](#11-testing-and-ci)
12. [Visual Layout and Architecture Diagrams](#12-visual-layout-and-architecture-diagrams)
13. [Appendix](#13-appendix)

---

## 1. Executive Summary

### 1.1 Product Vision

**SecuScan** is a local-first penetration testing platform designed to democratize security education while maintaining the highest standards of safety and ethical practice. Built on the principle that learning security should never compromise security, SecuScan operates entirely on the user's machine, eliminating the risks associated with cloud-based vulnerability scanning services and providing complete data sovereignty.

### 1.2 Target Personas

SecuScan serves two distinct but complementary user groups:

#### Persona A: The Learning Pentester
- **Profile:** Computer science students, cybersecurity certification candidates, self-taught security enthusiasts
- **Needs:** Structured workflows, guided experiences, clear explanations, low-risk experimentation environments
- **Pain Points:** Overwhelmed by command-line complexity, afraid of accidentally targeting production systems, lacks confidence in tool configuration
- **SecuScan Solution:** GUI-first experience with preset configurations, inline educational content, mandatory consent workflows, and sandbox-only execution by default

#### Persona B: The Power User
- **Profile:** Professional penetration testers, security researchers, DevSecOps engineers
- **Needs:** Scriptable automation, CLI access, customizable workflows, batch processing capabilities
- **Pain Points:** GUI tools lack flexibility, cloud services raise data sovereignty concerns, existing tools scattered across multiple systems
- **SecuScan Solution:** Full CLI access sharing the same preset library, API-driven automation, plugin extensibility, and composable workflows

### 1.3 Core Product Attributes

SecuScan is built on five foundational principles:

| Attribute | Description | Implementation |
|-----------|-------------|----------------|
| **Local-First** | Zero external dependencies, complete offline operation | All services run on 127.0.0.1, SQLite for persistence |
| **Safety-by-Default** | Prevent accidental harm through technical controls | Docker sandboxing, consent modals, rate limiting |
| **Educational** | Teaching tool first, professional tool second | Learning mode, inline help, narrated workflows |
| **Extensible** | Plugin architecture for community contributions | JSON metadata system, standardized API contracts |
| **Dual-Interface** | Support both GUI learners and CLI power users | Shared preset library, unified backend |

### 1.4 Product Purpose

**Mission Statement:**  
"Enable learning-driven, ethical penetration testing for academic and self-training use without exposing external systems or requiring a remote backend."

SecuScan bridges the gap between theoretical security knowledge and practical application. Students can safely experiment with professional-grade tools in controlled environments, while experienced practitioners benefit from a unified, privacy-respecting toolkit that doesn't send scan data to third-party services.

### 1.5 Major System Components

```
┌─────────────────────────────────────────────────────────┐
│                    SecuScan Platform                     │
├─────────────────────────────────────────────────────────┤
│  Frontend Layer                                          │
│  ├─ Lightweight SPA (React/Vue/Svelte)                  │
│  ├─ Dynamic Form Generator                              │
│  └─ Real-time Task Monitor                              │
├─────────────────────────────────────────────────────────┤
│  Backend Layer                                           │
│  ├─ Python FastAPI/Flask REST Server                    │
│  ├─ Plugin Loader & Registry                            │
│  ├─ Task Execution Engine                               │
│  └─ Output Parser & Normalizer                          │
├─────────────────────────────────────────────────────────┤
│  Data Layer                                              │
│  ├─ SQLite Database (tasks, plugins, settings, audit)   │
│  ├─ Filesystem Storage (raw outputs, reports)           │
│  └─ Encrypted Credential Vault                          │
├─────────────────────────────────────────────────────────┤
│  Execution Layer                                         │
│  ├─ Docker Container Orchestrator                       │
│  ├─ Namespace Isolation (fallback)                      │
│  └─ Resource Limiter                                    │
├─────────────────────────────────────────────────────────┤
│  Plugin Ecosystem                                        │
│  ├─ Core Tools (Nmap, Nikto, etc.)                     │
│  ├─ Community Plugins (verified)                        │
│  └─ Custom User Scripts                                 │
└─────────────────────────────────────────────────────────┘
```

### 1.6 Key Differentiators

**vs. Kali Linux:**  
SecuScan provides a curated, guided experience rather than a comprehensive toolkit. It's designed for learning specific workflows, not replacing a full penetration testing OS.

**vs. Burp Suite:**  
While Burp focuses on web application proxying and manual testing, SecuScan emphasizes automated scanning workflows with educational scaffolding.

**vs. Cloud Scanning Services (Qualys, Rapid7):**  
Complete data privacy—no scan results leave your machine. No subscription fees, no internet requirement, no compliance concerns.

### 1.7 Success Metrics

- **Educational Impact:** Users successfully complete guided pentesting workflows without external assistance
- **Safety Record:** Zero accidental scans of unauthorized targets
- **Adoption:** 1,000+ active users in first 6 months post-launch
- **Plugin Ecosystem:** 10+ community-contributed plugins within first year
- **User Satisfaction:** 4.5+ star rating on educational value

---

## 2. Tool Catalogue Overview

### 2.1 Evolution Philosophy

SecuScan's tool ecosystem follows a three-phase rollout strategy, prioritizing **safety, educational value, and practical utility** in that order. Each phase introduces tools with progressively higher risk profiles, accompanied by proportionally stronger safeguards.

```
Phase 1 (MVP)          Phase 2 (Expansion)      Phase 3 (Advanced)
───────────────        ────────────────────     ──────────────────
Network Recon    ──►   Subdomain Discovery ──►  Memory Forensics
Web Inspection   ──►   Injection Testing   ──►  Exploit Frameworks
Certificate Check──►   Secret Detection    ──►  Password Recovery
                       Code Analysis
```

### 2.2 MVP Tools (Phase 1)

The initial release includes five battle-tested tools, selected for their utility in foundational penetration testing workflows and relative safety when properly configured.

---

#### 2.2.1 Nmap (Network Mapper)

**Tool ID:** `nmap`  
**Binary:** `nmap` (+ `python-nmap` wrapper)  
**Category:** Network Discovery & Port Scanning  

##### Purpose
Nmap performs host discovery, port enumeration, service version detection, and OS fingerprinting. It's the industry standard for network reconnaissance and forms the foundation of most penetration testing engagements.

##### UI Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✓ | — | IP address, CIDR range, or hostname |
| `preset` | enum | ✗ | `quick` | Predefined scan profile |
| `ports` | string | ✗ | preset-dependent | Port specification (22,80,443 or 1-1000) |
| `scan_type` | enum | ✗ | `syn` | SYN/Connect/UDP scan mode |
| `timeout` | integer | ✗ | 300 | Maximum scan duration (seconds) |
| `threads` | integer | ✗ | 4 | Parallel scan threads |
| `safe_mode` | boolean | ✗ | `true` | Enable conservative timing/rate limits |

##### Preset Configurations

| Preset Name | Description | Parameters | Risk Level |
|-------------|-------------|------------|------------|
| **Quick Host Check** | Ping scan + top 100 ports | `--top-ports 100 -T3` | Low |
| **Top 1000 Ports** | Common service discovery | `--top-ports 1000 -T3` | Low |
| **Service Fingerprint** | Deep version detection | `-sV -sC --top-ports 1000 -T4` | Medium |
| **Comprehensive Scan** | Full port range + scripts | `-p- -sV -sC -T4` | High ⚠️ |

##### Output Structure

```json
{
  "scan_info": {
    "total_hosts": 1,
    "up_hosts": 1,
    "elapsed_time": 8.42
  },
  "hosts": [
    {
      "address": "192.168.1.100",
      "hostname": "webserver.local",
      "status": "up",
      "open_ports": [
        {
          "port": 22,
          "protocol": "tcp",
          "state": "open",
          "service": "ssh",
          "product": "OpenSSH",
          "version": "8.2p1",
          "cpe": "cpe:/a:openbsd:openssh:8.2p1"
        },
        {
          "port": 80,
          "protocol": "tcp",
          "state": "open",
          "service": "http",
          "product": "nginx",
          "version": "1.18.0"
        }
      ]
    }
  ]
}
```

##### Safety Controls

- **Localhost Restriction:** By default, only accepts `127.0.0.1`, `localhost`, or `192.168.x.x` targets
- **Aggressive Scan Protection:** Timing templates T4/T5 require explicit consent modal
- **Rate Limiting:** Maximum 10 scans per hour unless safe_mode disabled
- **Audit Logging:** All scan commands logged with timestamp and user consent flag

---

#### 2.2.2 HTTP Inspector

**Tool ID:** `http_inspector`  
**Library:** `requests` / `httpx`  
**Category:** Web Reconnaissance  

##### Purpose
Performs safe, read-only HTTP requests to validate endpoint availability, examine response headers, trace redirections, and inspect TLS configurations. Ideal for initial web target profiling without active exploitation attempts.

##### UI Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | ✓ | — | Target URL (http/https) |
| `follow_redirects` | boolean | ✗ | `true` | Follow 3xx redirect chains |
| `timeout` | integer | ✗ | 10 | Request timeout (seconds) |
| `verify_ssl` | boolean | ✗ | `true` | Validate TLS certificates |
| `custom_headers` | object | ✗ | `{}` | Key-value header pairs |
| `method` | enum | ✗ | `GET` | HTTP method (GET/HEAD/OPTIONS) |

##### Preset Configurations

| Preset Name | Parameters | Use Case |
|-------------|------------|----------|
| **Quick Fetch** | `follow_redirects=false, timeout=5` | Fast availability check |
| **Security Headers** | `method=HEAD, extract_headers=[security-related]` | Header analysis |
| **Full Inspection** | All options enabled | Comprehensive endpoint profile |

##### Output Structure

```json
{
  "request": {
    "url": "https://example.com/api",
    "method": "GET",
    "timestamp": "2025-10-29T14:20:30Z"
  },
  "response": {
    "status_code": 200,
    "reason": "OK",
    "elapsed_ms": 342,
    "headers": {
      "content-type": "application/json",
      "x-frame-options": "DENY",
      "strict-transport-security": "max-age=31536000"
    },
    "cookies": [
      {
        "name": "session_id",
        "secure": true,
        "httponly": true,
        "samesite": "Strict"
      }
    ],
    "redirect_chain": [
      "http://example.com → https://example.com (301)",
      "https://example.com → https://example.com/api (302)"
    ],
    "tls": {
      "version": "TLSv1.3",
      "cipher": "TLS_AES_256_GCM_SHA384",
      "certificate": {
        "issuer": "Let's Encrypt",
        "subject": "example.com",
        "valid_from": "2025-09-01",
        "valid_until": "2025-12-01",
        "san_domains": ["example.com", "www.example.com"]
      }
    }
  },
  "security_analysis": {
    "missing_headers": ["Content-Security-Policy", "X-Content-Type-Options"],
    "insecure_cookies": 0,
    "mixed_content_risk": false
  }
}
```

##### Risk Level
**Low** — Read-only operations, no injection attempts, no authentication bypass testing.

---

#### 2.2.3 Directory Discovery

**Tool ID:** `dir_brute`  
**Engine:** Custom Python (asyncio + httpx)  
**Category:** Web Enumeration  

##### Purpose
Discovers hidden directories, files, and endpoints by testing common naming patterns against a target web application. Uses wordlists to systematically probe for unlinked resources that may contain sensitive information or administrative interfaces.

##### UI Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `base_url` | string | ✓ | — | Root URL to scan |
| `wordlist` | enum/file | ✗ | `small` | Predefined list or custom upload |
| `extensions` | string | ✗ | `""` | Comma-separated extensions (.php,.html) |
| `threads` | integer | ✗ | 8 | Concurrent request workers |
| `delay_ms` | integer | ✗ | 50 | Milliseconds between requests |
| `match_codes` | string | ✗ | `200,301,302,403` | HTTP codes to report |
| `recursive` | boolean | ✗ | `false` | Scan discovered directories |
| `max_depth` | integer | ✗ | 2 | Recursion depth limit |

##### Preset Configurations

| Preset | Wordlist Size | Threads | Delay | Use Case |
|--------|---------------|---------|-------|----------|
| **Quick Discovery** | Small (500 entries) | 6 | 100ms | Fast, polite scan |
| **Standard Scan** | Medium (5,000 entries) | 8 | 50ms | Balanced approach |
| **Deep Discovery** | Large (50,000 entries) | 12 | 10ms | Comprehensive (Advanced) ⚠️ |

##### Wordlist Specifications

| List Name | Entries | Source | Contents |
|-----------|---------|--------|----------|
| `small` | 500 | Custom curated | Common directories (admin, api, backup, config, etc.) |
| `medium` | 5,000 | SecLists (filtered) | Web content + CMS patterns |
| `large` | 50,000 | Combined sources | Comprehensive discovery dictionary |

##### Output Structure

```json
{
  "scan_summary": {
    "base_url": "https://example.com",
    "wordlist": "medium",
    "total_requests": 5000,
    "duration_seconds": 127.4,
    "requests_per_second": 39.2,
    "discoveries": 12
  },
  "findings": [
    {
      "path": "/admin",
      "full_url": "https://example.com/admin",
      "status_code": 403,
      "response_size": 1024,
      "content_type": "text/html",
      "redirect_location": null,
      "notes": "Forbidden - admin panel exists"
    },
    {
      "path": "/api/v1",
      "status_code": 200,
      "response_size": 4562,
      "content_type": "application/json"
    },
    {
      "path": "/backup.zip",
      "status_code": 200,
      "response_size": 2048576,
      "content_type": "application/zip",
      "notes": "⚠️ Sensitive file exposure"
    }
  ]
}
```

##### Safety Controls

- **Default Rate Limiting:** 50ms delays prevent server overload
- **Consent Required:** Deep scans require explicit confirmation
- **Auto-Throttling:** Reduce speed on 429 (Too Many Requests) responses
- **Blacklist Protection:** Blocks scans against common production domains (unless explicitly overridden)
- **Request Cap:** Maximum 100,000 requests per scan

---

#### 2.2.4 Nikto/Wapiti (Web Passive Scanner)

**Tool ID:** `web_passive_scan`  
**Binary:** `nikto` / `wapiti`  
**Category:** Web Vulnerability Assessment  

##### Purpose
Automated scanner for common web server misconfigurations, outdated software versions, dangerous HTTP methods, missing security headers, and known vulnerabilities. Operates in two modes: passive (read-only) and active (includes low-risk probes).

##### UI Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target` | string | ✓ | — | Web application URL |
| `preset` | enum | ✗ | `passive` | Scan intensity level |
| `timeout` | integer | ✗ | 600 | Maximum scan duration |
| `safe_mode` | boolean | ✗ | `true` | Disable intrusive checks |
| `check_categories` | array | ✗ | `[all]` | Specific test categories |

##### Preset Configurations

| Preset | Description | Checks Included | Risk |
|--------|-------------|-----------------|------|
| **Passive Health** | Read-only analysis | Headers, versions, banner grabbing | Low |
| **Standard Scan** | Low-risk probes | + Common paths, methods, configs | Low-Medium |
| **Active Assessment** | Includes exploit checks | + SQL/XSS probes, auth bypass attempts | Medium-High ⚠️ |

##### Check Categories

- **Headers:** Security headers analysis (HSTS, CSP, X-Frame-Options)
- **SSL/TLS:** Certificate validation, cipher strength, protocol versions
- **Methods:** Dangerous HTTP methods (PUT, DELETE, TRACE)
- **Paths:** Sensitive files (.git, .env, backup files)
- **Versions:** Outdated software detection
- **Injections:** SQL/XSS/Command injection (active mode only)

##### Output Structure

```json
{
  "scan_info": {
    "target": "https://example.com",
    "start_time": "2025-10-29T14:20:30Z",
    "duration_seconds": 145,
    "safe_mode": true
  },
  "findings": [
    {
      "id": "OSVDB-3092",
      "severity": "medium",
      "category": "headers",
      "title": "Missing X-Content-Type-Options header",
      "description": "Browser MIME-type sniffing is not prevented",
      "references": ["https://owasp.org/..."],
      "remediation": "Add 'X-Content-Type-Options: nosniff' header"
    },
    {
      "id": "CVE-2021-12345",
      "severity": "high",
      "category": "versions",
      "title": "Outdated nginx version detected",
      "description": "nginx 1.14.0 has known vulnerabilities",
      "affected_component": "nginx/1.14.0",
      "remediation": "Upgrade to nginx 1.18.0+"
    }
  ],
  "severity_summary": {
    "critical": 0,
    "high": 1,
    "medium": 3,
    "low": 8,
    "info": 12
  }
}
```

##### Safety Controls

- **Safe Mode Enforcement:** Disables exploit attempts by default
- **Consent Modal:** Active scans display warning and require acknowledgment
- **Session Isolation:** Each scan runs in isolated Docker container
- **Result Sanitization:** Removes potentially executable payloads from reports

---

#### 2.2.5 TLS / Certificate Inspector

**Tool ID:** `tls_inspect`  
**Library:** `ssl` / `cryptography`  
**Category:** Transport Security Analysis  

##### Purpose
Examines TLS/SSL configurations, certificate validity, cipher suites, and protocol versions. Identifies weak cryptographic implementations, expired certificates, and misconfigured trust chains without performing any active exploitation.

##### UI Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `host` | string | ✓ | — | Hostname:port (e.g., example.com:443) |
| `show_chain` | boolean | ✗ | `true` | Display full certificate chain |
| `timeout` | integer | ✗ | 10 | Connection timeout |
| `check_ciphers` | boolean | ✗ | `true` | Test supported cipher suites |
| `check_protocols` | boolean | ✗ | `true` | Test TLS protocol versions |

##### Output Structure

```json
{
  "connection": {
    "host": "example.com",
    "port": 443,
    "ip": "93.184.216.34"
  },
  "certificate": {
    "subject": {
      "common_name": "example.com",
      "organization": "Example Corp",
      "country": "US"
    },
    "issuer": {
      "common_name": "Let's Encrypt Authority X3",
      "organization": "Let's Encrypt"
    },
    "validity": {
      "not_before": "2025-09-01T00:00:00Z",
      "not_after": "2025-12-01T23:59:59Z",
      "days_remaining": 33,
      "is_valid": true
    },
    "san": ["example.com", "www.example.com"],
    "signature_algorithm": "sha256WithRSAEncryption",
    "key_type": "RSA",
    "key_size": 2048,
    "serial_number": "03:AB:CD:EF...",
    "fingerprint_sha256": "4A:2B:..."
  },
  "chain": [
    {
      "level": 0,
      "subject": "example.com",
      "issuer": "Let's Encrypt Authority X3"
    },
    {
      "level": 1,
      "subject": "Let's Encrypt Authority X3",
      "issuer": "DST Root CA X3"
    }
  ],
  "protocol_support": {
    "SSLv2": false,
    "SSLv3": false,
    "TLSv1.0": false,
    "TLSv1.1": false,
    "TLSv1.2": true,
    "TLSv1.3": true
  },
  "cipher_suites": [
    {
      "name": "TLS_AES_256_GCM_SHA384",
      "protocol": "TLSv1.3",
      "strength": "strong"
    },
    {
      "name": "TLS_CHACHA20_POLY1305_SHA256",
      "protocol": "TLSv1.3",
      "strength": "strong"
    }
  ],
  "vulnerabilities": [
    {
      "id": "TLS_WEAK_CIPHER",
      "severity": "info",
      "description": "No weak ciphers detected"
    }
  ],
  "recommendations": [
    "Configuration is secure",
    "Certificate expires in 33 days - plan renewal"
  ]
}
```

##### Risk Level
**Minimal** — Passive observation only, no modification attempts.

---

### 2.3 Phase-2 Tools (Planned)

The following tools will be added in subsequent releases, following the same safety-first architecture:

#### 2.3.1 Subdomain Discovery
- **Tools:** `amass`, `subfinder`, DNS brute-forcing
- **Purpose:** Enumerate subdomains for attack surface mapping
- **Safety:** Rate-limited DNS queries, passive sources prioritized

#### 2.3.2 SQLMap Integration
- **Tool:** `sqlmap`
- **Purpose:** Automated SQL injection detection and exploitation
- **Safety:** Requires explicit consent, runs in isolated container, read-only by default

#### 2.3.3 Nuclei Template Scanner
- **Tool:** `nuclei`
- **Purpose:** Template-based vulnerability detection
- **Safety:** Curated template library, severity filtering

#### 2.3.4 Scapy Packet Analyzer
- **Tool:** `scapy`
- **Purpose:** Custom packet crafting and network analysis
- **Safety:** Localhost-only by default, raw socket permissions restricted

#### 2.3.5 Secret Detection
- **Tools:** `detect-secrets`, `gitleaks`
- **Purpose:** Scan codebases for exposed credentials
- **Safety:** File-only scanning, no network access

#### 2.3.6 Static Code Analysis
- **Tools:** `bandit` (Python), `semgrep` (multi-language)
- **Purpose:** Identify code-level security vulnerabilities
- **Safety:** Read-only file analysis

#### 2.3.7 SSH Command Runner
- **Purpose:** Execute commands on remote systems via SSH
- **Safety:** Requires explicit credential storage, audit logging, command whitelisting

---

### 2.4 Phase-3 Tools (Advanced)

High-risk tools requiring mature safety frameworks:

#### 2.4.1 Binary Analysis
- **Tools:** YARA, PE analyzers
- **Purpose:** Malware analysis and binary reverse engineering
- **Safety:** Sandboxed execution, VM-in-VM isolation

#### 2.4.2 Memory Forensics
- **Tool:** `volatility`
- **Purpose:** Memory dump analysis
- **Safety:** File-only, no live system access

#### 2.4.3 Metasploit Bridge
- **Tool:** `msfconsole` connector
- **Purpose:** Exploit framework integration
- **Safety:** Docker-only, requires advanced consent, audit logging

#### 2.4.4 Password Recovery
- **Tool:** `hashcat`
- **Purpose:** Hash cracking for security testing
- **Safety:** GPU isolation, local hash files only

---

## 3. UI and UX Architecture

### 3.1 Deployment Model

SecuScan runs as a **single-page web application (SPA)** served from a local Python backend. The entire application stack operates on `127.0.0.1`, eliminating network exposure risks.

**Access URL:** `http://127.0.0.1:8080`  
**Backend API:** `http://127.0.0.1:8080/api/v1`  

### 3.2 Visual Layout

The interface follows a dashboard-style layout optimized for both learning and productivity:

```
┌───────────────────────────────────────────────────────────────┐
│ [SecuScan Logo]              Status: ● Online    [⚙️ Settings] │ HEADER
├───────────────────────────────────────────────────────────────┤
│ SIDEBAR          │ MAIN CANVAS                                 │
│                  │                                             │
│ ⚡ Quick Scan    │ ┌─────────────────────────────────────┐    │
│                  │ │  Quick Scan                          │    │
│ 🔍 Network       │ │  Target: [________________]          │    │
│   • Nmap         │ │  Preset: [Quick Host Check ▾]       │    │
│   • Ping Sweep   │ │  [🛡️ Safe Mode: ON]  [▶ Start Scan] │    │
│                  │ └─────────────────────────────────────┘    │
│ 🌐 Web           │                                             │
│   • HTTP Insp.   │ ┌─────────────────┬──────────────────────┐ │
│   • Dir Discovery│ │ Tool Config      │ Live Output          │ │
│   • Nikto        │ │                  │                      │ │
│                  │ │ [Dynamic Form]   │ [Streaming Logs]     │ │
│ 🔐 Security      │ │                  │                      │ │
│   • TLS Check    │ │                  │ [Copy][Save][Clear]  │ │
│                  │ └─────────────────┴──────────────────────┘ │
│ 🧪 Learning      │                                             │
│   • Tutorials    │ ┌─────────────────────────────────────────┐ │
│   • Examples     │ │  Recent Tasks                            │ │
│                  │ │  [Task Cards: ID, Tool, Target, Status]  │ │
│ 📊 Reports       │ │  [View][Export][Delete]                  │ │
│                  │ └─────────────────────────────────────────┘ │
├──────────────────┴─────────────────────────────────────────────┤
│ ⚖️ SecuScan is for authorized testing only                     │ FOOTER
│ ☑️ I confirm I have permission to scan these targets           │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 Component Breakdown

#### 3.3.1 Header
- **Brand Identity:** SecuScan logo and version number
- **Connection Status:** Real-time backend health indicator (green dot = online)
- **Settings Menu:** Access to global configurations (network binding, sandbox preferences, theme)

#### 3.3.2 Left Sidebar (Tool Navigator)
Organizes tools into logical categories with visual hierarchy:

| Category | Icon | Tools |
|----------|------|-------|
| Quick Scan | ⚡ | One-click preset scans |
| Network | 🔍 | Nmap, ping, traceroute |
| Web | 🌐 | HTTP, directory discovery, web scanners |
| Security | 🔐 | TLS, certificate, security headers |
| Forensics | 🧬 | (Phase 3) Binary, memory analysis |
| Utilities | 🛠️ | Hash calculators, encoders |
| Learning | 🧪 | Guided tutorials, example targets |
| Reports | 📊 | Scan history and exports |

#### 3.3.3 Main Canvas

**Top Section: Quick Scan Card**
- Single-input scan initiation for beginners
- Target field with validation (highlights invalid IPs/URLs)
- Preset dropdown populated from plugin metadata
- Safe Mode toggle (large, prominent)
- Start button (disabled until consent checkbox checked)

**Middle-Left: Dynamic Tool Configuration**
- Form fields auto-generated from selected plugin's JSON metadata
- Collapsible "Advanced Options" section for power users
- Field validation with real-time error messages
- Preset selector that auto-populates fields
- "Save as Custom Preset" button

**Middle-Right: Live Output Panel**
- Tabbed interface: **Live Log** | **Structured Results** | **Raw Output**
- Live Log: Streaming text output with syntax highlighting
- Structured Results: Formatted tables/cards based on tool type
- Raw Output: Plaintext dump for copy-paste
- Action buttons: Copy to Clipboard, Save to File, Clear
- Auto-scroll toggle

**Bottom Section: Task History**
- Card-based layout showing recent scans
- Each card displays:
  - Task ID (clickable to load full results)
  - Tool name and icon
  - Target address
  - Status badge (Running/Completed/Failed/Cancelled)
  - Timestamp
  - Actions: View Results, Re-run, Export, Delete
- Pagination controls (10/25/50 per page)
- Filter by tool, date range, or status

#### 3.3.4 Footer
- **Legal Notice:** "SecuScan is for authorized testing only. Unauthorized scanning may be illegal."
- **Consent Checkbox:** Required for all scan initiations
- **Version Info:** Current release and update availability

### 3.4 Interaction Flow

#### Standard Scan Workflow

```
User Journey:
┌──────────────┐
│ 1. Select    │  User clicks tool from sidebar
│    Tool      │  → Tool configuration form loads
└──────┬───────┘
       │
┌──────▼───────┐
│ 2. Configure │  Fill required fields
│    Scan      │  Optional: Select preset or customize
└──────┬───────┘
       │
┌──────▼───────┐
│ 3. Review    │  Safe Mode status displayed
│    Safety    │  Risk warnings shown for intrusive tools
└──────┬───────┘
       │
┌──────▼───────┐
│ 4. Grant     │  Check consent checkbox
│    Consent   │  Additional modal for high-risk tools
└──────┬───────┘
       │
┌──────▼───────┐
│ 5. Execute   │  POST /task/start
│    Scan      │  Task ID returned
└──────┬───────┘
       │
┌──────▼───────┐
│ 6. Monitor   │  Server-Sent Events stream updates
│    Progress  │  Live log populates in real-time
└──────┬───────┘
       │
┌──────▼───────┐
│ 7. Review    │  Structured results render
│    Results   │  Raw output available
└──────┬───────┘
       │
┌──────▼───────┐
│ 8. Export/   │  JSON/CSV/PDF download
│    Archive   │  Task saved to history
└──────────────┘
```

#### Technical Flow

```
Frontend                Backend               Docker Sandbox
   │                       │                        │
   │──POST /task/start────>│                        │
   │                       │                        │
   │<──{task_id}──────────│                        │
   │                       │                        │
   │──SSE /task/123/stream>│                        │
   │                       │                        │
   │                       │──docker run───────────>│
   │                       │                        │
   │                       │<──stdout──────────────│
   │<──event: log─────────│                        │
   │                       │                        │
   │<──event: progress────│                        │
   │                       │                        │
   │                       │<──exit code───────────│
   │                       │                        │
   │                       │──parse output──>      │
   │<──event: complete────│                        │
   │                       │                        │
   │──GET /task/123/result>│                        │
   │<──{structured JSON}──│                        │
```

### 3.5 Responsive Design

While SecuScan is optimized for desktop use (minimum 1280x800), the interface gracefully adapts:

- **Desktop (1920x1080+):** Full layout with split panels
- **Laptop (1280x800):** Sidebar collapsible, stacked panels
- **Tablet (768x1024):** Sidebar hidden by default, single-column layout
- **Mobile:** Not officially supported (CLI recommended for mobile/tablet users)

### 3.6 Accessibility

- **Keyboard Navigation:** Full tab-order support, Ctrl+K command palette
- **Screen Reader:** ARIA labels on all interactive elements
- **Color Contrast:** WCAG AA compliance (4.5:1 minimum)
- **High Contrast Mode:** Toggle in settings for visual impairment
- **Reduced Motion:** Respects prefers-reduced-motion system setting

---

## 4. Plugin Metadata System

### 4.1 Architecture Philosophy

SecuScan's plugin system treats tools as **declarative configurations** rather than hardcoded integrations. Each tool is defined by a JSON metadata file that describes its interface, capabilities, and safety characteristics. The backend dynamically loads these files at startup, enabling:

- **Zero-Code Tool Addition:** Add new tools without modifying backend code
- **UI Auto-Generation:** Forms, help text, and validation rules derived from metadata
- **Consistent Behavior:** All tools follow the same execution and reporting patterns
- **Community Extensions:** Third-party plugins can be verified and installed

### 4.2 Metadata Schema

#### Full Schema Definition

```json
{
  "id": "unique_tool_identifier",
  "name": "Display Name",
  "version": "1.0.0",
  "description": "Brief tool description (shown in sidebar)",
  "long_description": "Detailed explanation for help panel (Markdown supported)",
  "category": "network|web|security|forensics|utility",
  "author": {
    "name": "Author Name",
    "email": "author@example.com",
    "url": "https://github.com/author"
  },
  "license": "MIT",
  "icon": "🔍",
  "engine": {
    "type": "cli|python|docker",
    "binary": "/usr/bin/nmap",
    "docker_image": "secuscan/nmap:latest",
    "entrypoint": "python3 /app/scanner.py"
  },
  "command_template": [
    "{binary}",
    "-sV",
    "{target}",
    "--if:safe_mode:then:-T3:else:-T4",
    "--if:ports:then:-p {ports}"
  ],
  "fields": [
    {
      "id": "target",
      "label": "Target",
      "type": "string",
      "required": true,
      "default": "",
      "placeholder": "192.168.1.1 or example.com",
      "validation": {
        "pattern": "^[a-zA-Z0-9.-]+$",
        "message": "Must be valid IP or hostname"
      },
      "help": "IP address, hostname, or CIDR range to scan"
    },
    {
      "id": "preset",
      "label": "Scan Preset",
      "type": "select",
      "required": false,
      "default": "quick",
      "options": [
        {"value": "quick", "label": "Quick Host Check"},
        {"value": "standard", "label": "Standard Scan"},
        {"value": "deep", "label": "Deep Scan (Advanced)"}
      ],
      "help": "Predefined configuration profiles"
    },
    {
      "id": "safe_mode",
      "label": "Safe Mode",
      "type": "boolean",
      "required": false,
      "default": true,
      "help": "Enable conservative timing and rate limits"
    }
  ],
  "presets": {
    "quick": {
      "ports": "100",
      "scan_type": "syn",
      "safe_mode": true
    },
    "standard": {
      "ports": "1000",
      "scan_type": "syn",
      "safe_mode": true
    },
    "deep": {
      "ports": "all",
      "scan_type": "connect",
      "safe_mode": false
    }
  },
  "output": {
    "format": "json|xml|text",
    "parser": "builtin_nmap|custom",
    "schema": {
      "hosts": "array",
      "ports": "array",
      "services": "array"
    }
  },
  "safety": {
    "level": "safe|intrusive|exploit",
    "requires_consent": true,
    "consent_message": "This scan may trigger IDS alerts. Proceed?",
    "allowed_targets": ["127.0.0.1", "192.168.*.*", "10.*.*.*"],
    "rate_limit": {
      "max_per_hour": 10,
      "max_concurrent": 2
    }
  },
  "learning": {
    "difficulty": "beginner|intermediate|advanced",
    "estimated_duration": "2 minutes",
    "tutorial_url": "https://docs.secuscan.local/nmap"
  },
  "dependencies": {
    "binaries": ["nmap"],
    "python_packages": ["python-nmap==0.7.1"],
    "system_packages": ["libpcap-dev"]
  },
  "checksum": "sha256:abcdef123456...",
  "signature": "GPG signature for verification"
}
```

### 4.3 Field Type Reference

| Type | UI Control | Validation | Example |
|------|-----------|------------|---------|
| `string` | Text input | Regex pattern | `192.168.1.1` |
| `text` | Textarea | Length limits | Multi-line config |
| `integer` | Number input | Min/max range | `1-65535` |
| `boolean` | Toggle switch | N/A | `true`/`false` |
| `select` | Dropdown | Options list | `quick/standard/deep` |
| `multiselect` | Checkbox group | Options list | `[ssh, http, ftp]` |
| `file` | File upload | Extension filter | `.txt, .csv` |
| `keyvalue` | Key-value table | JSON schema | `{"User-Agent": "..."}` |

### 4.4 Command Template Syntax

The `command_template` field supports conditional logic and variable substitution:

**Syntax Elements:**

```
{variable}                    → Direct substitution
{variable:default_value}      → Use default if variable empty
--if:condition:then:A:else:B  → Conditional insertion
--each:list:template          → Iterate over array
```

**Examples:**

```json
[
  "nmap",
  "-sV",
  "{target}",
  "--if:safe_mode:then:-T3:else:-T4",
  "--if:ports:then:-p {ports}",
  "--each:scripts:then:--script {item}"
]
```

Rendered with `{target: "192.168.1.1", safe_mode: true, ports: "80,443"}`:
```bash
nmap -sV 192.168.1.1 -T3 -p 80,443
```

### 4.5 Parser System

Plugins can specify how their output should be parsed:

#### Built-in Parsers

| Parser ID | Format | Tools |
|-----------|--------|-------|
| `builtin_nmap` | Nmap XML | Nmap scans |
| `builtin_nikto` | Nikto CSV | Nikto/Wapiti |
| `builtin_json` | JSON | Custom scripts |
| `builtin_xml` | Generic XML | Various |
| `builtin_regex` | Regex extraction | Log parsers |

#### Custom Parsers

Plugins can provide Python parser scripts:

```python
# plugins/nmap/parser.py
def parse(raw_output: str, task_config: dict) -> dict:
    """
    Parse Nmap XML output into standardized format.
    
    Returns:
        {
            "summary": ["Found 2 hosts", "12 open ports"],
            "structured": {...},
            "severity_counts": {"high": 0, "medium": 2, "low": 5}
        }
    """
    import xml.etree.ElementTree as ET
    
    root = ET.fromstring(raw_output)
    hosts = []
    
    for host in root.findall('.//host'):
        # ... parsing logic ...
        hosts.append(host_data)
    
    return {
        "summary": [f"Found {len(hosts)} hosts"],
        "structured": {"hosts": hosts},
        "severity_counts": calculate_severity(hosts)
    }
```

### 4.6 Plugin Loading and Validation

#### Load Sequence

```
Application Startup
│
├─1─> Scan plugins/ directory
│
├─2─> Load *.json files
│
├─3─> Validate schema
│     ├─ Required fields present
│     ├─ Field types correct
│     └─ Command template valid
│
├─4─> Verify signatures (if enabled)
│     ├─ Check GPG signature
│     └─ Validate checksum
│
├─5─> Check dependencies
│     ├─ Binary availability
│     ├─ Python packages
│     └─ Docker images
│
├─6─> Register plugin
│     ├─ Add to plugin registry
│     ├─ Cache metadata
│     └─ Enable in UI
│
└─7─> Log status (loaded/failed)
```

#### Validation Rules

- **Schema Compliance:** Must match JSON schema definition
- **Unique ID:** No duplicate plugin IDs
- **Binary Existence:** Check binary paths if engine=cli
- **Docker Image:** Verify image availability if engine=docker
- **Safety Classification:** Valid safety level
- **Signature (Optional):** Valid GPG signature from trusted key

### 4.7 Plugin Directory Structure

```
plugins/
├── nmap/
│   ├── metadata.json       # Plugin definition
│   ├── parser.py           # Output parser
│   ├── icon.svg            # Optional custom icon
│   ├── README.md           # Documentation
│   └── examples/           # Example configurations
│       ├── quick_scan.json
│       └── deep_scan.json
├── http_inspector/
│   ├── metadata.json
│   ├── parser.py
│   └── requirements.txt    # Python dependencies
├── dir_brute/
│   ├── metadata.json
│   ├── wordlists/
│   │   ├── small.txt
│   │   ├── medium.txt
│   │   └── large.txt
│   └── Dockerfile          # Custom Docker image
└── ...
```

---

## 5. Backend API Contract

### 5.1 API Versioning

**Base URL:** `http://127.0.0.1:8080/api/v1`  
**Protocol:** REST over HTTP  
**Serialization:** JSON  
**Authentication:** Token-based (optional, disabled by default)  

### 5.2 Endpoint Reference

#### 5.2.1 Health & Status

##### GET /health

Returns backend operational status and system information.

**Request:**
```http
GET /api/v1/health HTTP/1.1
Host: 127.0.0.1:8080
```

**Response:**
```json
{
  "status": "operational",
  "version": "0.1.0",
  "uptime_seconds": 3600,
  "system": {
    "platform": "Linux",
    "python_version": "3.11.5",
    "docker_available": true,
    "plugins_loaded": 5
  },
  "limits": {
    "max_concurrent_tasks": 3,
    "max_tasks_per_hour": 50
  }
}
```

---

#### 5.2.2 Plugin Management

##### GET /plugins

Lists all available plugins with metadata summary.

**Request:**
```http
GET /api/v1/plugins HTTP/1.1
```

**Response:**
```json
{
  "plugins": [
    {
      "id": "nmap",
      "name": "Nmap",
      "category": "network",
      "safety_level": "safe",
      "enabled": true,
      "icon": "🔍"
    },
    {
      "id": "http_inspector",
      "name": "HTTP Inspector",
      "category": "web",
      "safety_level": "safe",
      "enabled": true,
      "icon": "🌐"
    }
  ],
  "total": 5
}
```

---

##### GET /plugin/{id}/schema

Returns full plugin metadata including field definitions and presets.

**Request:**
```http
GET /api/v1/plugin/nmap/schema HTTP/1.1
```

**Response:**
```json
{
  "id": "nmap",
  "name": "Nmap",
  "description": "Network discovery and port scanning",
  "fields": [
    {
      "id": "target",
      "label": "Target",
      "type": "string",
      "required": true,
      "placeholder": "192.168.1.1",
      "validation": {
        "pattern": "^[a-zA-Z0-9.-]+$"
      }
    }
  ],
  "presets": {
    "quick": {
      "ports": "100",
      "safe_mode": true
    }
  },
  "safety": {
    "level": "safe",
    "requires_consent": true
  }
}
```

---

##### GET /presets

Returns all preset configurations aggregated across plugins.

**Response:**
```json
{
  "nmap": {
    "quick": {...},
    "standard": {...}
  },
  "dir_brute": {
    "quick": {...},
    "deep": {...}
  }
}
```

---

#### 5.2.3 Task Execution

##### POST /task/start

Initiates a new plugin execution task.

**Request:**
```http
POST /api/v1/task/start HTTP/1.1
Content-Type: application/json

{
  "plugin_id": "nmap",
  "preset": "quick",
  "inputs": {
    "target": "192.168.1.100",
    "safe_mode": true
  },
  "consent_granted": true
}
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "created_at": "2025-10-29T14:20:30Z",
  "stream_url": "/api/v1/task/550e8400-e29b-41d4-a716-446655440000/stream"
}
```

**Error Response (400):**
```json
{
  "error": "validation_failed",
  "message": "Target field is required",
  "field": "target"
}
```

---

##### GET /task/{id}/status

Returns current task status.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 45,
  "started_at": "2025-10-29T14:20:35Z",
  "elapsed_seconds": 12
}
```

**Status Values:**
- `queued` — Waiting for execution slot
- `running` — Currently executing
- `completed` — Finished successfully
- `failed` — Execution error
- `cancelled` — User-terminated

---

##### GET /task/{id}/stream

Server-Sent Events stream for real-time updates.

**Response (SSE):**
```
event: log
data: {"timestamp": "14:20:35", "message": "Starting Nmap scan..."}

event: progress
data: {"percent": 25, "current": "Scanning port 80"}

event: log
data: {"timestamp": "14:20:40", "message": "Found open port: 22/tcp"}

event: complete
data: {"status": "completed", "duration": 8.2}
```

---

##### GET /task/{id}/result

Returns standardized scan results.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "plugin_id": "nmap",
  "tool": "Nmap",
  "target": "192.168.1.100",
  "timestamp": "2025-10-29T14:20:30Z",
  "duration_seconds": 8.2,
  "status": "completed",
  "summary": [
    "Scan completed in 8.2 seconds",
    "Found 1 host up",
    "Discovered 3 open ports"
  ],
  "severity_counts": {
    "critical": 0,
    "high": 0,
    "medium": 1,
    "low": 2,
    "info": 5
  },
  "structured": {
    "hosts": [
      {
        "address": "192.168.1.100",
        "status": "up",
        "open_ports": [...]
      }
    ]
  },
  "raw_output_path": "/data/raw/550e8400-e29b-41d4-a716-446655440000.txt"
}
```

---

##### POST /task/cancel

Terminates a running task.

**Request:**
```http
POST /api/v1/task/550e8400-e29b-41d4-a716-446655440000/cancel HTTP/1.1
```

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2025-10-29T14:21:00Z"
}
```

---

#### 5.2.4 Task Management

##### GET /tasks

Lists all tasks with pagination and filtering.

**Query Parameters:**
- `page` (int, default=1)
- `per_page` (int, default=25, max=100)
- `plugin_id` (string, optional)
- `status` (enum, optional)
- `date_from` (ISO8601, optional)
- `date_to` (ISO8601, optional)

**Request:**
```http
GET /api/v1/tasks?page=1&per_page=25&plugin_id=nmap&status=completed HTTP/1.1
```

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "...",
      "plugin_id": "nmap",
      "target": "192.168.1.100",
      "status": "completed",
      "created_at": "2025-10-29T14:20:30Z",
      "duration_seconds": 8.2
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total_pages": 4,
    "total_items": 93
  }
}
```

---

##### DELETE /task/{id}

Deletes a task and its associated data.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true
}
```

---

#### 5.2.5 Reports & Export

##### GET /reports/{id}

Downloads task results in specified format.

**Query Parameters:**
- `format` (enum: `json`|`csv`|`pdf`)

**Request:**
```http
GET /api/v1/reports/550e8400-e29b-41d4-a716-446655440000?format=pdf HTTP/1.1
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="nmap_scan_20251029_142030.pdf"

[PDF binary data]
```

---

#### 5.2.6 Settings

##### GET /settings

Returns current global settings.

**Response:**
```json
{
  "network": {
    "bind_address": "127.0.0.1",
    "port": 8080,
    "allow_remote": false
  },
  "sandbox": {
    "engine": "docker",
    "default_timeout": 600,
    "resource_limits": {
      "cpu_quota": 0.5,
      "memory_mb": 512
    }
  },
  "safety": {
    "require_consent": true,
    "safe_mode_default": true,
    "allowed_networks": ["127.0.0.1", "192.168.*.*"]
  }
}
```

---

##### POST /settings

Updates global settings.

**Request:**
```json
{
  "safety": {
    "safe_mode_default": false
  }
}
```

**Response:**
```json
{
  "updated": true,
  "settings": {...}
}
```

---

### 5.3 Authentication

By default, SecuScan runs without authentication (localhost-only binding is the security boundary). Optional token-based auth can be enabled:

**Header:**
```http
Authorization: Bearer <token>
```

Tokens generated via:
```bash
secuscan auth generate --expires 30d
```

---

### 5.4 Rate Limiting

**Global Limits:**
- 100 requests/minute per client
- 50 task starts per hour
- 3 concurrent running tasks

**Response Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1698595200
```

**Rate Limit Response (429):**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Maximum 50 tasks per hour allowed",
  "retry_after": 1800
}
```

---

## 6. Standardized Output Schema

### 6.1 Unified Result Format

All plugins produce output conforming to a standardized schema, enabling consistent UI rendering, export formats, and result aggregation.

### 6.2 Core Schema

```json
{
  "task_id": "uuid-v4",
  "plugin_id": "string",
  "tool": "string (display name)",
  "target": "string",
  "timestamp": "ISO8601 datetime",
  "duration_seconds": "float",
  "status": "completed|failed|cancelled",
  "exit_code": "integer (null if N/A)",
  
  "summary": [
    "Human-readable summary line 1",
    "Human-readable summary line 2"
  ],
  
  "severity_counts": {
    "critical": "integer",
    "high": "integer",
    "medium": "integer",
    "low": "integer",
    "info": "integer"
  },
  
  "structured": {
    "tool-specific-key": "tool-specific-value"
  },
  
  "raw_output_path": "string (file path)",
  "raw_output_excerpt": "string (first 1000 chars, optional)",
  
  "errors": [
    {
      "code": "string",
      "message": "string",
      "timestamp": "ISO8601"
    }
  ],
  
  "metadata": {
    "inputs": {"target": "...", "preset": "..."},
    "environment": {
      "sandbox": "docker",
      "container_id": "abc123",
      "resource_usage": {
        "cpu_seconds": 12.5,
        "memory_peak_mb": 256
      }
    }
  }
}
```

### 6.3 Tool-Specific Structured Formats

#### 6.3.1 Nmap Output

```json
{
  "structured": {
    "scan_info": {
      "type": "SYN",
      "protocol": "tcp",
      "num_services": 1000,
      "services": "1-1000"
    },
    "hosts": [
      {
        "address": "192.168.1.100",
        "hostname": "webserver.local",
        "status": "up",
        "reason": "echo-reply",
        "ports": [
          {
            "port": 22,
            "protocol": "tcp",
            "state": "open",
            "reason": "syn-ack",
            "service": {
              "name": "ssh",
              "product": "OpenSSH",
              "version": "8.2p1",
              "extrainfo": "Ubuntu Linux",
              "confidence": 10,
              "cpe": ["cpe:/a:openbsd:openssh:8.2p1"]
            },
            "scripts": {
              "ssh-hostkey": "RSA key fingerprint: ..."
            }
          }
        ],
        "os": {
          "matches": [
            {
              "name": "Linux 5.4",
              "accuracy": 95,
              "cpe": "cpe:/o:linux:linux_kernel:5.4"
            }
          ]
        }
      }
    ]
  }
}
```

#### 6.3.2 HTTP Inspector Output

```json
{
  "structured": {
    "request": {
      "url": "https://example.com",
      "method": "GET",
      "headers_sent": {"User-Agent": "SecuScan/1.0"}
    },
    "response": {
      "status_code": 200,
      "status_text": "OK",
      "elapsed_ms": 342,
      "headers": {
        "content-type": "text/html",
        "server": "nginx/1.18.0",
        "x-frame-options": "DENY",
        "strict-transport-security": "max-age=31536000"
      },
      "cookies": [
        {
          "name": "session_id",
          "value": "[REDACTED]",
          "domain": ".example.com",
          "path": "/",
          "secure": true,
          "httponly": true,
          "samesite": "Strict",
          "expires": "2025-10-30T14:20:30Z"
        }
      ],
      "redirects": [
        {"from": "http://example.com", "to": "https://example.com", "code": 301},
        {"from": "https://example.com", "to": "https://example.com/", "code": 301}
      ],
      "tls": {
        "version": "TLSv1.3",
        "cipher": "TLS_AES_256_GCM_SHA384",
        "certificate": {
          "subject": "example.com",
          "issuer": "Let's Encrypt",
          "valid_from": "2025-09-01",
          "valid_until": "2025-12-01",
          "days_remaining": 33,
          "san": ["example.com", "www.example.com"],
          "signature_algorithm": "sha256WithRSAEncryption"
        }
      }
    },
    "security_analysis": {
      "score": 85,
      "missing_headers": ["Content-Security-Policy"],
      "weak_configurations": [],
      "recommendations": ["Add CSP header"]
    }
  }
}
```

#### 6.3.3 Directory Discovery Output

```json
{
  "structured": {
    "scan_config": {
      "base_url": "https://example.com",
      "wordlist": "medium",
      "extensions": [".php", ".html"],
      "total_requests": 5000
    },
    "statistics": {
      "duration_seconds": 127.4,
      "requests_per_second": 39.2,
      "responses_by_code": {
        "200": 8,
        "301": 2,
        "403": 1,
        "404": 4989
      }
    },
    "findings": [
      {
        "path": "/admin",
        "url": "https://example.com/admin",
        "status_code": 403,
        "size_bytes": 1024,
        "content_type": "text/html",
        "response_time_ms": 45,
        "redirect_location": null,
        "severity": "medium",
        "notes": "Forbidden - admin panel exists but protected"
      },
      {
        "path": "/backup.zip",
        "url": "https://example.com/backup.zip",
        "status_code": 200,
        "size_bytes": 2048576,
        "content_type": "application/zip",
        "response_time_ms": 1200,
        "severity": "high",
        "notes": "⚠️ Sensitive file exposure"
      }
    ]
  }
}
```

#### 6.3.4 Web Scanner (Nikto) Output

```json
{
  "structured": {
    "target": "https://example.com",
    "scan_duration": 145,
    "tests_performed": 6700,
    "findings": [
      {
        "id": "OSVDB-3092",
        "severity": "medium",
        "category": "headers",
        "title": "Missing X-Content-Type-Options header",
        "description": "The anti-MIME-sniffing header X-Content-Type-Options was not set to 'nosniff'",
        "url": "https://example.com/",
        "method": "GET",
        "evidence": "(Header not present)",
        "references": [
          "https://owasp.org/www-project-secure-headers/#x-content-type-options",
          "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Content-Type-Options"
        ],
        "remediation": "Add 'X-Content-Type-Options: nosniff' to HTTP response headers",
        "cvss_score": 5.3
      },
      {
        "id": "CVE-2021-12345",
        "severity": "high",
        "category": "version",
        "title": "Outdated nginx version detected",
        "description": "nginx 1.14.0 is outdated and contains known vulnerabilities",
        "affected_component": "nginx/1.14.0",
        "remediation": "Upgrade to nginx 1.18.0 or later",
        "cvss_score": 7.5
      }
    ],
    "categories": {
      "headers": 3,
      "ssl": 1,
      "methods": 0,
      "paths": 2,
      "versions": 1,
      "injections": 0
    }
  }
}
```

#### 6.3.5 TLS Inspector Output

```json
{
  "structured": {
    "connection": {
      "host": "example.com",
      "port": 443,
      "ip_address": "93.184.216.34",
      "connected": true
    },
    "certificate": {
      "version": 3,
      "serial_number": "03:AB:CD:EF:12:34:56:78",
      "subject": {
        "common_name": "example.com",
        "organization": "Example Corp",
        "organizational_unit": "IT",
        "locality": "San Francisco",
        "state": "CA",
        "country": "US"
      },
      "issuer": {
        "common_name": "Let's Encrypt Authority X3",
        "organization": "Let's Encrypt",
        "country": "US"
      },
      "validity": {
        "not_before": "2025-09-01T00:00:00Z",
        "not_after": "2025-12-01T23:59:59Z",
        "is_valid": true,
        "days_remaining": 33
      },
      "san": [
        "example.com",
        "www.example.com",
        "api.example.com"
      ],
      "public_key": {
        "algorithm": "RSA",
        "size": 2048,
        "exponent": 65537
      },
      "signature_algorithm": "sha256WithRSAEncryption",
      "fingerprints": {
        "sha1": "4A:2B:3C:...",
        "sha256": "8F:1E:2D:..."
      }
    },
    "chain": [
      {
        "level": 0,
        "subject": "example.com",
        "issuer": "Let's Encrypt Authority X3",
        "expires": "2025-12-01"
      },
      {
        "level": 1,
        "subject": "Let's Encrypt Authority X3",
        "issuer": "DST Root CA X3",
        "expires": "2030-09-30"
      }
    ],
    "chain_valid": true,
    "protocol_support": {
      "SSLv2": {"supported": false, "note": "Deprecated"},
      "SSLv3": {"supported": false, "note": "Deprecated"},
      "TLSv1.0": {"supported": false, "note": "Insecure"},
      "TLSv1.1": {"supported": false, "note": "Insecure"},
      "TLSv1.2": {"supported": true, "note": "Secure"},
      "TLSv1.3": {"supported": true, "note": "Preferred"}
    },
    "cipher_suites": [
      {
        "name": "TLS_AES_256_GCM_SHA384",
        "protocol": "TLSv1.3",
        "key_exchange": "ECDHE",
        "encryption": "AES-256-GCM",
        "mac": "AEAD",
        "strength": "strong"
      },
      {
        "name": "TLS_CHACHA20_POLY1305_SHA256",
        "protocol": "TLSv1.3",
        "strength": "strong"
      }
    ],
    "vulnerabilities": {
      "heartbleed": false,
      "poodle": false,
      "beast": false,
      "crime": false,
      "freak": false,
      "logjam": false
    },
    "security_score": 95,
    "recommendations": [
      "Configuration is secure",
      "Certificate expires in 33 days - plan renewal"
    ]
  }
}
```

### 6.4 Severity Classification

Findings are categorized using industry-standard severity levels:

| Level | Description | CVSS Range | UI Color |
|-------|-------------|------------|----------|
| **Critical** | Immediate exploitation risk, requires urgent action | 9.0-10.0 | Red |
| **High** | Significant security weakness, high priority | 7.0-8.9 | Orange |
| **Medium** | Moderate risk, should be addressed | 4.0-6.9 | Yellow |
| **Low** | Minor issue, low exploitation likelihood | 0.1-3.9 | Blue |
| **Info** | Informational finding, no direct risk | 0.0 | Gray |

---

## 7. Database and Storage Layout

### 7.1 Database Technology

**Engine:** SQLite 3.35+  
**Location:** `$HOME/.secuscan/secuscan.db`  
**Encryption:** Optional (SQLCipher extension)  
**Backup:** Automatic daily snapshots to `$HOME/.secuscan/backups/`  

### 7.2 Database Schema

#### Table: `tasks`

Stores all scan task records and their execution state.

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,  -- UUID v4
    plugin_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    target TEXT NOT NULL,
    inputs_json TEXT NOT NULL,  -- JSON string of input parameters
    preset TEXT,
    
    status TEXT NOT NULL,  -- queued|running|completed|failed|cancelled
    consent_granted BOOLEAN NOT NULL DEFAULT 0,
    safe_mode BOOLEAN NOT NULL DEFAULT 1,
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,
    duration_seconds REAL,
    
    exit_code INTEGER,
    structured_json TEXT,  -- Parsed output in standard format
    raw_output_path TEXT,
    error_message TEXT,
    
    -- Resource tracking
    container_id TEXT,
    cpu_seconds REAL,
    memory_peak_mb REAL,
    
    -- Indexes
    FOREIGN KEY (plugin_id) REFERENCES plugins(id)
);

CREATE INDEX idx_tasks_created ON tasks(created_at DESC);
CREATE INDEX idx_tasks_target ON tasks(target);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_plugin ON tasks(plugin_id);
```

#### Table: `plugins`

Plugin registry and configuration.

```sql
CREATE TABLE plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    category TEXT NOT NULL,
    metadata_json TEXT NOT NULL,  -- Full plugin metadata
    
    enabled BOOLEAN NOT NULL DEFAULT 1,
    checksum TEXT,  -- SHA-256 of metadata file
    signature TEXT,  -- GPG signature (optional)
    
    installed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_updated DATETIME,
    last_used DATETIME,
    
    -- Dependency tracking
    binary_path TEXT,
    docker_image TEXT,
    python_packages_json TEXT
);

CREATE INDEX idx_plugins_category ON plugins(category);
```

#### Table: `settings`

Global application configuration.

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL,  -- string|integer|boolean|json
    description TEXT,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Example rows:
INSERT INTO settings VALUES 
    ('bind_address', '127.0.0.1', 'string', 'Server bind address', CURRENT_TIMESTAMP),
    ('bind_port', '8080', 'integer', 'Server port', CURRENT_TIMESTAMP),
    ('require_consent', '1', 'boolean', 'Force consent checkbox', CURRENT_TIMESTAMP),
    ('max_concurrent_tasks', '3', 'integer', 'Concurrent task limit', CURRENT_TIMESTAMP);
```

#### Table: `audit_log`

Security audit trail for compliance and forensics.

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,  -- task_start|task_complete|consent_granted|setting_change|auth_attempt
    severity TEXT NOT NULL,  -- info|warning|error
    
    user_id TEXT,  -- If authentication enabled
    ip_address TEXT,
    
    message TEXT NOT NULL,
    context_json TEXT,  -- Additional structured data
    
    task_id TEXT,  -- Link to task if applicable
    plugin_id TEXT
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_event ON audit_log(event_type);
CREATE INDEX idx_audit_task ON audit_log(task_id);
```

#### Table: `presets`

User-defined custom presets (supplements plugin defaults).

```sql
CREATE TABLE presets (
    id TEXT PRIMARY KEY,  -- UUID v4
    name TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    config_json TEXT NOT NULL,
    
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used DATETIME,
    use_count INTEGER DEFAULT 0,
    
    FOREIGN KEY (plugin_id) REFERENCES plugins(id),
    UNIQUE(plugin_id, name)
);
```

### 7.3 Filesystem Storage

#### Directory Structure

```
$HOME/.secuscan/
├── secuscan.db                # SQLite database
├── backups/                   # Automatic DB backups
│   ├── secuscan_2025-10-29.db
│   └── secuscan_2025-10-28.db
├── data/
│   ├── raw/                   # Raw tool outputs
│   │   ├── {task_id}.txt
│   │   ├── {task_id}.xml
│   │   └── {task_id}.json
│   └── reports/               # Exported reports
│       ├── {task_id}.json
│       ├── {task_id}.csv
│       └── {task_id}.pdf
├── plugins/                   # Plugin definitions
│   ├── nmap/
│   │   ├── metadata.json
│   │   └── parser.py
│   └── http_inspector/
│       └── metadata.json
├── wordlists/                 # Directory scanner dictionaries
│   ├── small.txt
│   ├── medium.txt
│   └── large.txt
├── credentials/               # Encrypted credential vault
│   └── vault.enc
└── logs/                      # Application logs
    ├── secuscan.log
    └── access.log
```

#### File Rotation and Cleanup

**Raw Outputs:**
- Retained for 30 days by default
- Configurable retention period: 7/30/90/365 days or indefinite
- Manual cleanup via UI or `secuscan clean --older-than 30d`

**Database Backups:**
- Daily snapshots at 2 AM local time
- Retained for 7 days (configurable)
- Compressed with gzip to save space

**Logs:**
- Rotated daily
- Maximum 10 MB per log file
- Compressed older than 7 days
- Retained for 30 days

### 7.4 Data Export Formats

#### JSON Export
Full structured export including all metadata:
```json
{
  "task": {...},
  "results": {...},
  "metadata": {...}
}
```

#### CSV Export
Flattened results suitable for spreadsheet import:
```csv
Task ID,Plugin,Target,Timestamp,Status,Duration,Finding Type,Severity,Description
...
```

#### PDF Export
Professional report format:
- Executive summary
- Methodology
- Findings table with severity color-coding
- Detailed results
- Recommendations
- Technical appendix

---

## 8. Sandboxing and Security Layer

### 8.1 Defense-in-Depth Architecture

SecuScan implements multiple overlapping security controls to prevent accidental harm, unauthorized access, and data exfiltration.

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Network Isolation                          │
│ • Bind to 127.0.0.1 only by default                 │
│ • No external listening sockets                     │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│ Layer 2: Execution Sandbox                          │
│ • Docker containers with restricted capabilities    │
│ • Read-only filesystem (except /tmp)                │
│ • Limited network access                            │
│ • Resource quotas (CPU, memory, disk)               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│ Layer 3: Plugin Verification                        │
│ • Whitelist of allowed plugins                      │
│ • GPG signature validation                          │
│ • Checksum verification                             │
│ • Dependency scanning                               │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│ Layer 4: Input Validation                           │
│ • Target address filtering                          │
│ • Command injection prevention                      │
│ • Path traversal protection                         │
│ • Preset parameter validation                       │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│ Layer 5: User Consent                               │
│ • Mandatory checkbox for all scans                  │
│ • Modal dialogs for intrusive tools                 │
│ • Clear risk communication                          │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│ Layer 6: Audit Logging                              │
│ • All actions logged with timestamps                │
│ • Immutable audit trail                             │
│ • Consent flags recorded                            │
└─────────────────────────────────────────────────────┘
```

### 8.2 Network Isolation

#### Localhost-Only Binding

**Default Configuration:**
```yaml
network:
  bind_address: "127.0.0.1"
  bind_port: 8080
  allow_remote_access: false
```

**Enforcement:**
- Backend server validates bind address on startup
- Refuses to start if 0.0.0.0 binding attempted without explicit override
- Warning message displayed if remote access enabled

#### Firewall-Friendly

SecuScan requires no inbound connections, making it compatible with restrictive firewall policies.

### 8.3 Docker Sandbox Execution

Every scan runs in an isolated Docker container with strict resource limits and capability restrictions.

#### Container Configuration

```yaml
# Docker Compose snippet
services:
  scanner:
    image: secuscan/scanner:latest
    network_mode: "bridge"  # Isolated network
    cap_drop:
      - ALL
    cap_add:
      - NET_RAW      # Required for Nmap SYN scans
      - NET_ADMIN    # Required for packet capture
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined  # (Only for tools requiring raw sockets)
    read_only: true
    tmpfs:
      - /tmp:size=100M,mode=1777
    volumes:
      - ./data/raw:/output:rw
      - ./plugins:/plugins:ro
    environment:
      - TASK_ID=${TASK_ID}
      - PLUGIN_ID=${PLUGIN_ID}
    resources:
      limits:
        cpus: '0.5'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 256M
```

#### Runtime Security

**Filesystem:**
- Root filesystem read-only
- `/tmp` writable but memory-backed (ephemeral)
- Output directory mounted with write-only permissions
- Plugin directory mounted read-only

**Network:**
- Bridge network with egress filtering
- DNS resolution allowed
- HTTP/HTTPS allowed for web tools
- Raw sockets restricted to specific tools

**Processes:**
- Single process per container
- Automatic termination after timeout
- No shell access
- PID namespace isolation

### 8.4 Namespace Isolation (Fallback)

If Docker is unavailable, SecuScan falls back to Linux namespace isolation:

```python
import os
import subprocess

def run_sandboxed(command, timeout=300):
    """
    Execute command in isolated namespace.
    Requires: Linux kernel with namespace support
    """
    sandbox_command = [
        "unshare",
        "--pid",        # PID namespace
        "--net",        # Network namespace
        "--mount",      # Mount namespace
        "--fork",       # Fork to ensure PID 1 in new namespace
        "timeout", str(timeout),
        *command
    ]
    
    result = subprocess.run(
        sandbox_command,
        capture_output=True,
        text=True,
        check=False
    )
    
    return result
```

**Limitations:**
- Less isolation than Docker
- Requires root or specific capabilities
- Recommended for development/testing only

### 8.5 Plugin Verification

#### Whitelist System

**Trusted Plugin Registry:**
```json
{
  "trusted_plugins": [
    {
      "id": "nmap",
      "checksum": "sha256:abc123...",
      "signature": "-----BEGIN PGP SIGNATURE-----...",
      "verified_at": "2025-10-15T00:00:00Z"
    }
  ],
  "trusted_signers": [
    {
      "name": "SecuScan Official",
      "fingerprint": "1234 5678 90AB CDEF",
      "public_key_url": "https://secuscan.local/keys/official.asc"
    }
  ]
}
```

#### Verification Process

```
Plugin Load Request
│
├─1─> Check if plugin ID in whitelist
│     └─ If not: Reject (unless user override enabled)
│
├─2─> Compute SHA-256 checksum
│     └─ Compare with expected value
│
├─3─> Verify GPG signature (if present)
│     └─ Check against trusted signer keys
│
├─4─> Scan for malicious patterns
│     └─ Command injection attempts
│     └─ Path traversal attempts
│     └─ Suspicious network calls
│
└─5─> Load plugin if all checks pass
```

### 8.6 Input Validation

#### Target Address Filtering

**Allowed by Default:**
- `127.0.0.1`, `localhost`, `::1`
- Private IP ranges: `192.168.0.0/16`, `10.0.0.0/8`, `172.16.0.0/12`
- Explicit hostnames (if user confirms)

**Blocked by Default:**
- Public IP ranges (unless safe mode disabled)
- Known cloud provider ranges (AWS, GCP, Azure) to prevent accidental cloud scanning
- Government/military TLDs (.mil, .gov)

**Validation Logic:**
```python
import ipaddress
import re

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),       # Broadcast
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("224.0.0.0/4"),     # Multicast
]

ALLOWED_PRIVATE = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
]

def validate_target(target: str, safe_mode: bool = True) -> tuple[bool, str]:
    """
    Validate scan target address.
    
    Returns: (is_valid, error_message)
    """
    try:
        ip = ipaddress.ip_address(target)
        
        # Check blocked networks
        if any(ip in net for net in BLOCKED_NETWORKS):
            return False, "Target is in blocked network range"
        
        # Safe mode: only allow private IPs
        if safe_mode and not any(ip in net for net in ALLOWED_PRIVATE):
            return False, "Public IPs not allowed in safe mode"
        
        return True, ""
        
    except ValueError:
        # Not an IP, check if hostname
        if not re.match(r'^[a-zA-Z0-9.-]+$', target):
            return False, "Invalid hostname format"
        
        if target.endswith(('.mil', '.gov')) and safe_mode:
            return False, "Government domains blocked in safe mode"
        
        return True, ""
```

#### Command Injection Prevention

All user inputs are escaped before shell execution:

```python
import shlex

def build_command(template: list, inputs: dict) -> list:
    """
    Build command from template with safe substitution.
    Uses list-based commands to prevent shell injection.
    """
    command = []
    for token in template:
        # Handle conditionals
        if token.startswith("--if:"):
            parts = token.split(":")
            condition = inputs.get(parts[1], False)
            value = parts[3] if condition else parts[5]
            if value:
                command.append(value)
        # Handle variables
        elif "{" in token:
            # Extract variable name
            var_name = token.strip("{}")
            value = inputs.get(var_name, "")
            # Validate and escape
            if value:
                command.append(str(value))
        else:
            command.append(token)
    
    return command  # Return as list, not shell string
```

### 8.7 Rate Limiting

#### Per-Tool Limits

| Tool | Max/Hour | Max Concurrent | Timeout |
|------|----------|----------------|---------|
| Nmap | 10 | 2 | 300s |
| HTTP Inspector | 100 | 5 | 30s |
| Dir Discovery | 5 | 1 | 600s |
| Nikto | 3 | 1 | 600s |
| TLS Inspector | 50 | 3 | 30s |

#### Enforcement Mechanism

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self):
        self.task_history = defaultdict(list)  # plugin_id -> [timestamps]
    
    def can_execute(self, plugin_id: str, max_per_hour: int) -> tuple[bool, str]:
        """Check if plugin can be executed based on rate limits."""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Clean old entries
        self.task_history[plugin_id] = [
            ts for ts in self.task_history[plugin_id]
            if ts > hour_ago
        ]
        
        recent_count = len(self.task_history[plugin_id])
        
        if recent_count >= max_per_hour:
            return False, f"Rate limit exceeded: {recent_count}/{max_per_hour} per hour"
        
        self.task_history[plugin_id].append(now)
        return True, ""
```

### 8.8 Credential Storage

Credentials for SSH, API tokens, etc. are encrypted at rest using industry-standard encryption.

**Storage Format:**
```python
# Encrypted vault using Fernet (symmetric encryption)
from cryptography.fernet import Fernet

class CredentialVault:
    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.key = self._load_or_generate_key()
        self.cipher = Fernet(self.key)
    
    def store(self, name: str, value: str):
        """Encrypt and store credential."""
        encrypted = self.cipher.encrypt(value.encode())
        # Store encrypted value in DB
        db.execute(
            "INSERT OR REPLACE INTO credentials VALUES (?, ?)",
            (name, encrypted)
        )
    
    def retrieve(self, name: str) -> str:
        """Decrypt and retrieve credential."""
        encrypted = db.query("SELECT value FROM credentials WHERE name = ?", name)
        return self.cipher.decrypt(encrypted).decode()
```

**Key Management:**
- Master key derived from system keyring (macOS Keychain, Windows Credential Manager, Linux Secret Service)
- Fallback to file-based key with appropriate permissions (0600)
- Key rotation supported via `secuscan credentials rotate-key`

### 8.9 Consent Workflows

#### Standard Consent (All Tools)

```
┌────────────────────────────────────────────┐
│  ⚖️ Ethical Scanning Agreement             │
├────────────────────────────────────────────┤
│                                            │
│  By proceeding, you confirm:               │
│                                            │
│  ☑️ You own or have explicit written      │
│     permission to test the target system   │
│                                            │
│  ☑️ You understand this may trigger       │
│     security monitoring systems            │
│                                            │
│  ☑️ You accept responsibility for your    │
│     actions and any consequences           │
│                                            │
│  [ ] I have read and agree to these terms  │
│                                            │
│      [Cancel]      [I Agree, Proceed]      │
└────────────────────────────────────────────┘
```

#### High-Risk Tool Modal (Intrusive/Exploit Tools)

```
┌────────────────────────────────────────────┐
│  ⚠️ HIGH-RISK TOOL WARNING                 │
├────────────────────────────────────────────┤
│                                            │
│  Tool: SQLMap (SQL Injection Tester)       │
│  Risk Level: HIGH                          │
│                                            │
│  This tool will attempt to exploit         │
│  vulnerabilities and may:                  │
│                                            │
│  • Modify database contents                │
│  • Trigger security alerts                 │
│  • Cause service disruption                │
│  • Leave forensic evidence                 │
│                                            │
│  ONLY use on systems you own or have       │
│  explicit written authorization to test.   │
│                                            │
│  Unauthorized use may violate:             │
│  • Computer Fraud and Abuse Act (CFAA)     │
│  • Local/international computer crime laws │
│                                            │
│  Type "I UNDERSTAND" to proceed:           │
│  [____________________________________]     │
│                                            │
│      [Cancel]      [Proceed Anyway]        │
└────────────────────────────────────────────┘
```

---

## 9. UX, Legal, and Learning Tools

### 9.1 Learning Mode

SecuScan includes a dedicated **Learning Mode** designed to guide beginners through penetration testing concepts without risk.

#### Features

**1. Safe Practice Environments**

Pre-configured local targets:
- `test.secuscan.local` — Intentionally vulnerable web app (custom Flask app)
- `practice.secuscan.local` — Misconfigured services for port scanning practice
- `secure.secuscan.local` — Properly hardened reference implementation

**2. Guided Tutorials**

Step-by-step walkthroughs with interactive elements:

```
┌─────────────────────────────────────────────────┐
│ Tutorial: Your First Port Scan                  │
├─────────────────────────────────────────────────┤
│                                                 │
│ 📚 Concept: Port Scanning                       │
│ Port scanning discovers which network services  │
│ are running on a target system.                 │
│                                                 │
│ 🎯 Goal                                         │
│ Scan practice.secuscan.local to discover        │
│ open ports and identify services.               │
│                                                 │
│ 📋 Steps                                        │
│ 1. Select "Nmap" from the Network category      │
│    [✓] Completed                                │
│                                                 │
│ 2. Enter target: practice.secuscan.local        │
│    [✓] Completed                                │
│                                                 │
│ 3. Choose "Quick Host Check" preset             │
│    [ ] Complete this step                       │
│    [Show me where]                              │
│                                                 │
│ 4. Click "Start Scan"                           │
│    [ ] Waiting...                               │
│                                                 │
│      [Previous]  [Skip Tutorial]  [Next]        │
└─────────────────────────────────────────────────┘
```

**3. Narrated Results**

Educational annotations explain scan output:

```json
{
  "port": 22,
  "service": "ssh",
  "educational_note": "SSH (Secure Shell) is used for secure remote access. Port 22 is the default. Finding this open suggests remote administration is enabled.",
  "learn_more_url": "/docs/services/ssh"
}
```

**4. Progress Tracking**

Gamification elements:
- Tutorial completion badges
- Tool mastery levels (Beginner → Intermediate → Advanced)
- Challenge scenarios with solutions

### 9.2 Inline Contextual Help

Every tool and field includes educational content:

```
┌──────────────────────────────────────────┐
│ Target [?]                               │
│ [192.168.1.1____________________]        │
│                                          │
│ 💡 What's a target?                      │
│ The IP address or hostname of the system │
│ you want to scan. Examples:              │
│ • 192.168.1.1 (single IP)                │
│ • 192.168.1.0/24 (subnet range)          │
│ • example.com (hostname)                 │
│                                          │
│ ⚠️ Only scan systems you own or have     │
│ permission to test.                      │
│                                          │
│ [📖 Learn more about targeting]          │
└──────────────────────────────────────────┘
```

### 9.3 Legal Safeguards

#### Consent Tracking

Every scan records legal consent:

```sql
INSERT INTO audit_log (
    event_type,
    severity,
    message,
    context_json
) VALUES (
    'consent_granted',
    'info',
    'User granted consent for Nmap scan',
    json('{"task_id": "...","target": "192.168.1.1", "tool": "nmap", "ip_address": "127.0.0.1", "timestamp": "2025-10-29T14:20:30Z"}')
);
```

#### Liability Disclaimer

Displayed on first launch (must be accepted once):

```markdown
# SecuScan Terms of Use

## Legal Notice

SecuScan is a penetration testing tool designed for:
- Educational purposes
- Authorized security testing
- Personal skill development

## User Responsibilities

By using SecuScan, you agree that:

1. **Authorization Required:** You will only scan systems you own or have explicit written permission to test.

2. **Legal Compliance:** You are responsible for understanding and complying with all applicable laws in your jurisdiction.

3. **No Warranty:** This software is provided "as is" without warranty. The authors are not liable for misuse.

4. **Ethical Use:** You will use this tool ethically and responsibly.

## Legal References

Unauthorized computer scanning may violate:
- USA: Computer Fraud and Abuse Act (18 USC § 1030)
- UK: Computer Misuse Act 1990
- EU: Directive 2013/40/EU
- [Your jurisdiction's laws]

Penalties may include fines and imprisonment.

## Acceptance

☑️ I have read, understood, and agree to these terms.

[Decline]  [Accept and Continue]
```

#### Export Watermarking

All PDF reports include legal footer:

```
This report was generated by SecuScan for authorized security testing.
Unauthorized scanning may be illegal. Ensure you have proper authorization
before conducting any penetration tests.

Report ID: 550e8400-e29b-41d4-a716-446655440000
Generated: 2025-10-29 14:20:30 UTC
Scan authorized by: [User confirmation recorded]
```

### 9.4 Export and Reporting Features

#### PDF Report Structure

```
┌─────────────────────────────────────────┐
│  SECURITY ASSESSMENT REPORT             │
│  Generated by SecuScan v0.1.0           │
└─────────────────────────────────────────┘

1. EXECUTIVE SUMMARY
   • Scan Type: Nmap Port Scan
   • Target: 192.168.1.100
   • Date: October 29, 2025
   • Duration: 8.2 seconds
   • Findings: 3 open ports, 1 medium severity

2. METHODOLOGY
   • Tool: Nmap 7.94
   • Scan Type: SYN scan (-sS)
   • Ports: Top 1000
   • Safe Mode: Enabled

3. KEY FINDINGS
   [Table with color-coded severity]
   
4. DETAILED RESULTS
   [Port-by-port breakdown with service details]

5. RECOMMENDATIONS
   • Update OpenSSH to latest version
   • Review nginx configuration
   • Implement rate limiting

6. TECHNICAL APPENDIX
   [Raw command output]

────────────────────────────────────────────
Legal Notice: This scan was conducted with
proper authorization. Report ID: [UUID]
```

#### Report Templates

Users can create custom report templates:

```json
{
  "template_name": "PCI-DSS Compliance Scan",
  "sections": [
    {"type": "summary", "include": true},
    {"type": "findings_table", "filter_severity": ["high", "critical"]},
    {"type": "compliance_mapping", "framework": "PCI-DSS"},
    {"type": "remediation", "include": true},
    {"type": "technical_details", "include": false}
  ],
  "branding": {
    "logo": "/path/to/logo.png",
    "company_name": "ACME Security",
    "footer_text": "Confidential"
  }
}
```

### 9.5 Accessibility Features

- **Keyboard Shortcuts:** Full navigation without mouse
- **Screen Reader Support:** ARIA labels and semantic HTML
- **High Contrast Mode:** Alternative color scheme for visual impairments
- **Font Scaling:** Respects browser zoom settings
- **Focus Indicators:** Clear visual feedback for keyboard navigation

---

## 10. Packaging and Installation

### 10.1 Distribution Formats

SecuScan is available in multiple formats to suit different deployment scenarios:

| Format | Platform | Use Case |
|--------|----------|----------|
| **Docker Compose** | All | Recommended for most users |
| **Python Package** | Linux/macOS | Native installation |
| **Standalone Binary** | Windows | Single-file executable |
| **Source** | All | Development/customization |

### 10.2 Docker Compose Deployment

#### File: `docker-compose.yml`

```yaml
version: '3.8'

services:
  gui:
    image: secuscan/gui:latest
    container_name: secuscan_gui
    ports:
      - "127.0.0.1:8080:8080"
    volumes:
      - ./data:/app/data
      - ./plugins:/app/plugins:ro
      - /var/run/docker.sock:/var/run/docker.sock  # For spawning scanner containers
    environment:
      - SECUSCAN_BIND=0.0.0.0:8080
      - SECUSCAN_DB=/app/data/secuscan.db
      - SECUSCAN_SAFE_MODE=true
    restart: unless-stopped
    networks:
      - secuscan_network

  # Scanner containers are spawned dynamically by gui service

networks:
  secuscan_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

volumes:
  data:
  plugins:
```

#### Installation Steps

```bash
# 1. Download docker-compose.yml
curl -O https://secuscan.local/releases/latest/docker-compose.yml

# 2. Start services
docker-compose up -d

# 3. Verify
curl http://127.0.0.1:8080/health

# 4. Open browser
open http://127.0.0.1:8080
```

### 10.3 Native Python Installation

#### File: `install.sh`

```bash
#!/bin/bash
set -e

echo "SecuScan Installer v0.1.0"
echo "========================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.9.0"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.9+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "✓ Python $PYTHON_VERSION detected"

# Check Docker
if command -v docker &> /dev/null; then
    echo "✓ Docker detected"
    DOCKER_AVAILABLE=true
else
    echo "⚠️  Docker not found (optional, but recommended)"
    DOCKER_AVAILABLE=false
fi

# Create installation directory
INSTALL_DIR="$HOME/.secuscan"
mkdir -p "$INSTALL_DIR"/{data,plugins,wordlists,logs}

# Install Python package
echo "Installing SecuScan..."
pip3 install --user secuscan

# Download plugins
echo "Downloading core plugins..."
secuscan plugin install --official nmap http_inspector dir_brute nikto tls_inspect

# Download wordlists
echo "Downloading wordlists..."
curl -o "$INSTALL_DIR/wordlists/small.txt" https://secuscan.local/wordlists/small.txt
curl -o "$INSTALL_DIR/wordlists/medium.txt" https://secuscan.local/wordlists/medium.txt

# Create systemd service (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    cat > "$HOME/.config/systemd/user/secuscan.service" <<EOF
[Unit]
Description=SecuScan Pentesting Toolkit
After=network.target

[Service]
Type=simple
ExecStart=$(which secuscan) serve --bind 127.0.0.1:8080
Restart=on-failure

[Install]
WantedBy=default.target
EOF

    systemctl --user enable secuscan
    systemctl --user start secuscan
    echo "✓ Systemd service installed"
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "Start SecuScan:"
echo "  secuscan serve"
echo ""
echo "Or access via browser:"
echo "  http://127.0.0.1:8080"
```

### 10.4 Windows Binary (PyInstaller)

#### Build Script: `build_windows.py`

```python
import PyInstaller.__main__
import os

PyInstaller.__main__.run([
    'secuscan/main.py',
    '--name=SecuScan',
    '--onefile',
    '--windowed',
    '--icon=assets/secuscan.ico',
    '--add-data=plugins:plugins',
    '--add-data=wordlists:wordlists',
    '--add-data=templates:templates',
    '--hidden-import=secuscan.plugins',
    '--clean',
])
```

**Distribution:**
- Single `.exe` file (~50 MB)
- Includes embedded Python interpreter
- Auto-extracts resources to `%APPDATA%\SecuScan`
- Creates desktop shortcut

### 10.5 Plugin Distribution

#### Plugin Package Format

```
secuscan-plugin-nmap-1.0.0.tar.gz
├── manifest.json
├── metadata.json
├── parser.py
├── README.md
├── LICENSE
└── checksums.txt
```

#### Installation Command

```bash
# Install from official repository
secuscan plugin install nmap

# Install from file
secuscan plugin install ./secuscan-plugin-nmap-1.0.0.tar.gz

# Install from URL
secuscan plugin install https://example.com/plugin.tar.gz --verify-signature
```

#### Plugin Signature Verification

```bash
# Generate signature (plugin author)
gpg --detach-sign --armor secuscan-plugin-nmap-1.0.0.tar.gz

# Verify signature (user)
gpg --verify secuscan-plugin-nmap-1.0.0.tar.gz.asc secuscan-plugin-nmap-1.0.0.tar.gz
```

### 10.6 Licensing

**Core Application:** MIT License

```
MIT License

Copyright (c) 2025 SecuScan Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

[Standard MIT License text]
```

**Plugin Compatibility:**
- MIT-licensed plugins preferred
- GPL plugins allowed (must be clearly marked)
- Proprietary plugins supported (user must accept separate license)

---

## 11. Testing and CI

### 11.1 Testing Strategy

SecuScan employs a comprehensive testing pyramid:

```
        ╱╲
       ╱  ╲  E2E Tests (Selenium)
      ╱────╲  • Full user workflows
     ╱      ╲ • Cross-browser testing
    ╱ ────── ╲
   ╱          ╲ Integration Tests (pytest)
  ╱   ──────   ╲ • API contracts
 ╱              ╲ • Plugin loading
╱  ────────────  ╲ • Sandbox execution
╱                ╲
──────────────────── Unit Tests (pytest)
                     • Validation logic
                     • Parsers
                     • Utilities
```

### 11.2 Unit Tests

**Coverage Target:** 85%

**Example Test:**

```python
# tests/unit/test_validation.py
import pytest
from secuscan.validation import validate_target

def test_validate_target_localhost():
    is_valid, msg = validate_target("127.0.0.1", safe_mode=True)
    assert is_valid is True
    assert msg == ""

def test_validate_target_public_ip_safe_mode():
    is_valid, msg = validate_target("8.8.8.8", safe_mode=True)
    assert is_valid is False
    assert "Public IPs not allowed" in msg

def test_validate_target_private_ip():
    is_valid, msg = validate_target("192.168.1.1", safe_mode=True)
    assert is_valid is True

def test_validate_target_invalid_format():
    is_valid, msg = validate_target("not..a..valid..ip", safe_mode=True)
    assert is_valid is False
    assert "Invalid" in msg

@pytest.mark.parametrize("target,safe_mode,expected", [
    ("127.0.0.1", True, True),
    ("8.8.8.8", True, False),
    ("8.8.8.8", False, True),
    ("example.com", True, True),
    ("malicious.mil", True, False),
])
def test_validate_target_matrix(target, safe_mode, expected):
    is_valid, _ = validate_target(target, safe_mode=safe_mode)
    assert is_valid == expected
```

### 11.3 Integration Tests

**Test Scenarios:**

1. **Plugin Loading:**
   - Load all core plugins
   - Verify metadata schema
   - Check dependencies

2. **Task Execution:**
   - Create task via API
   - Monitor status updates
   - Retrieve results

3. **Sandbox Isolation:**
   - Verify container creation
   - Test network restrictions
   - Confirm filesystem isolation

**Example:**

```python
# tests/integration/test_task_execution.py
import pytest
import requests
import time

@pytest.fixture
def api_client():
    return "http://127.0.0.1:8080/api/v1"

def test_nmap_scan_workflow(api_client):
    # Start scan
    response = requests.post(f"{api_client}/task/start", json={
        "plugin_id": "nmap",
        "preset": "quick",
        "inputs": {"target": "scanme.nmap.org"},
        "consent_granted": True
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Poll until complete
    for _ in range(30):
        status_response = requests.get(f"{api_client}/task/{task_id}/status")
        status = status_response.json()["status"]
        if status == "completed":
            break
        time.sleep(1)
    
    assert status == "completed"
    
    # Retrieve results
    result_response = requests.get(f"{api_client}/task/{task_id}/result")
    result = result_response.json()
    
    assert "structured" in result
    assert "hosts" in result["structured"]
    assert len(result["structured"]["hosts"]) > 0
```

### 11.4 End-to-End Tests

**Tools:** Selenium, Playwright

**Test Cases:**

```python
# tests/e2e/test_user_workflows.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_first_scan_workflow():
    driver = webdriver.Chrome()
    driver.get("http://127.0.0.1:8080")
    
    # Accept terms
    consent_checkbox = driver.find_element(By.ID, "consent-checkbox")
    consent_checkbox.click()
    
    # Select tool
    driver.find_element(By.LINK_TEXT, "Nmap").click()
    
    # Fill form
    target_input = driver.find_element(By.ID, "target")
    target_input.send_keys("scanme.nmap.org")
    
    # Select preset
    preset_select = driver.find_element(By.ID, "preset")
    preset_select.send_keys("Quick Host Check")
    
    # Start scan
    start_button = driver.find_element(By.ID, "start-scan")
    start_button.click()
    
    # Wait for completion
    WebDriverWait(driver, 60).until(
        EC.text_to_be_present_in_element((By.ID, "task-status"), "Completed")
    )
    
    # Verify results displayed
    results_panel = driver.find_element(By.ID, "structured-results")
    assert "open ports" in results_panel.text.lower()
    
    driver.quit()
```

### 11.5 CI/CD Pipeline

**Platform:** GitHub Actions

#### `.github/workflows/ci.yml`

```yaml
name: SecuScan CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install flake8 black mypy
      - name: Lint code
        run: |
          flake8 secuscan/ --max-line-length=100
          black --check secuscan/
          mypy secuscan/ --strict

  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run unit tests
        run: |
          pytest tests/unit/ --cov=secuscan --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  test-integration:
    runs-on: ubuntu-latest
    services:
      docker:
        image: docker:20.10
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Start SecuScan
        run: |
          docker-compose up -d
          sleep 10
      - name: Run integration tests
        run: |
          pytest tests/integration/

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - name: Install Chrome
        uses: browser-actions/setup-chrome@latest
      - name: Start SecuScan
        run: |
          docker-compose up -d
          sleep 10
      - name: Run E2E tests
        run: |
          pytest tests/e2e/

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r secuscan/ -f json -o bandit-report.json
      - name: Run Safety
        run: |
          pip install safety
          safety check --json

  build-docker:
    runs-on: ubuntu-latest
    needs: [lint, test-unit, test-integration]
    steps:
      - uses: actions/checkout@v3
      - name: Build image
        run: |
          docker build -t secuscan/gui:${{ github.sha }} .
      - name: Push to registry
        if: github.ref == 'refs/heads/main'
        run: |
          docker push secuscan/gui:${{ github.sha }}
          docker tag secuscan/gui:${{ github.sha }} secuscan/gui:latest
          docker push secuscan/gui:latest
```

### 11.6 Week-by-Week Development Roadmap

#### Week 0: Project Setup
- ✅ Initialize repository structure
- ✅ Set up CI/CD pipeline
- ✅ Define coding standards
- ✅ Create project documentation

#### Week 1: Core Architecture
- **Plugin System**
  - JSON metadata parser
  - Plugin registry
  - Dynamic form generator
- **API Foundation**
  - FastAPI server setup
  - Health check endpoint
  - Plugin listing endpoints
- **Task Engine**
  - Task queue implementation
  - Status tracking
  - Basic execution framework

#### Week 2: Sandbox & Security
- **Docker Integration**
  - Container orchestration
  - Resource limits
  - Network isolation
- **Validation Layer**
  - Target address filtering
  - Input sanitization
  - Rate limiting
- **Logging & Audit**
  - Audit trail implementation
  - Consent recording
  - Error logging

#### Week 3: Tool Integration
- **MVP Plugins**
  - Nmap integration + parser
  - HTTP Inspector
  - TLS Inspector
  - Directory Discovery
  - Nikto integration
- **Output Parsing**
  - Standardized schema implementation
  - Tool-specific parsers
  - Error handling

#### Week 4: Frontend & Reporting
- **GUI Implementation**
  - React/Vue SPA
  - Tool selection interface
  - Live output streaming
  - Task history view
- **Reporting**
  - JSON export
  - CSV export
  - PDF generation
- **Documentation**
  - User guide
  - API documentation
  - Plugin development guide

#### Week 5: Testing & Polish
- **Testing**
  - Unit test coverage ≥85%
  - Integration tests
  - E2E workflows
- **Performance**
  - Load testing
  - Resource optimization
  - Database indexing
- **Security Review**
  - Penetration testing
  - Code audit
  - Dependency scanning

#### Week 6: Release Preparation
- **Packaging**
  - Docker images
  - Python package
  - Windows binary
- **Distribution**
  - GitHub release
  - Documentation site
  - Demo video
- **Launch**
  - Announcement
  - Community outreach
  - Bug triage process

---

## 12. Visual Layout and Architecture Diagrams

### 12.1 System Overview Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Web Browser (127.0.0.1:8080)              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │
│  │  │ Tool     │ │ Config   │ │ Live     │ │ Task         │  │ │
│  │  │ Selector │ │ Form     │ │ Output   │ │ History      │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │
│  └────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP/SSE
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BACKEND API SERVER                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  FastAPI / Flask                                            │ │
│  │  • REST Endpoints (/plugins, /task/*, /reports/*)          │ │
│  │  • Server-Sent Events (task streaming)                     │ │
│  │  • Authentication (optional)                               │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────────┐ │
│  │ Plugin Loader  │ │ Task Executor  │ │ Output Parser      │ │
│  │ • JSON parser  │ │ • Queue mgmt   │ │ • Schema mapping   │ │
│  │ • Validation   │ │ • Sandbox spawn│ │ • Result storage   │ │
│  └────────────────┘ └────────────────┘ └────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
        ┌───────────────┐ ┌──────────┐ ┌─────────────┐
        │ Docker Engine │ │ SQLite   │ │ Filesystem  │
        │ (Sandboxing)  │ │ Database │ │ Storage     │
        └───────────────┘ └──────────┘ └─────────────┘
                │               │             │
                ▼               ▼             ▼
    ┌──────────────────┐   ┌────────┐   ┌─────────┐
    │ Scanner          │   │ tasks  │   │ data/   │
    │ Container        │   │ plugins│   │ raw/    │
    │ • nmap           │   │ settings│  │ reports/│
    │ • nikto          │   │ audit  │   └─────────┘
    │ • custom tools   │   └────────┘
    │                  │
    │ [Isolated Env]   │
    └──────────────────┘
```

### 12.2 Plugin Loader Flow

```
Application Startup
        │
        ▼
┌─────────────────┐
│ Scan plugins/   │
│ directory       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│ For each        │──────>│ Load         │
│ *.json file     │       │ metadata.json│
└────────┬────────┘       └──────┬───────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │ Validate Schema │
         │              │ • Required      │
         │              │   fields?       │
         │              │ • Valid types?  │
         │              └────────┬────────┘
         │                       │
         │              ┌────────▼────────┐
         │              │ Valid?          │
         │              └────────┬────────┘
         │                       │
         │              YES ◄────┼────► NO
         │               │               │
         │               ▼               ▼
         │      ┌─────────────────┐  ┌──────────┐
         │      │ Check           │  │ Log      │
         │      │ Dependencies    │  │ Error &  │
         │      │ • Binary exists?│  │ Skip     │
         │      │ • Docker image? │  └──────────┘
         │      └────────┬────────┘
         │               │
         │               ▼
         │      ┌─────────────────┐
         │      │ Verify Signature│
         │      │ (if enabled)    │
         │      └────────┬────────┘
         │               │
         │               ▼
         │      ┌─────────────────┐
         │      │ Register Plugin │
         │      │ • Add to        │
         │      │   registry      │
         │      │ • Cache metadata│
         │      │ • Enable in UI  │
         │      └────────┬────────┘
         │               │
         └───────────────┘
                │
                ▼
       ┌─────────────────┐
       │ Plugins Ready   │
       │ Load complete   │
       └─────────────────┘
```

### 12.3 Task Lifecycle Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         TASK LIFECYCLE                           │
└─────────────────────────────────────────────────────────────────┘

User Action: Click "Start Scan"
        │
        ▼
┌─────────────────┐
│ 1. CREATE       │  POST /task/start
│    • Generate   │  • Validate inputs
│      task_id    │  • Check consent
│    • Status:    │  • Verify rate limits
│      queued     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 2. QUEUE        │  • Add to execution queue
│    • Wait for   │  • Respect max_concurrent
│      available  │  • Priority ordering
│      slot       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 3. SPAWN        │  • Create Docker container
│    • Status:    │  • Mount volumes
│      running    │  • Set resource limits
│    • Container  │  • Start tool process
│      created    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. EXECUTE      │  • Stream stdout/stderr
│    • Run tool   │  • Update progress
│    • Monitor    │  • Handle timeouts
│      progress   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. COLLECT      │  • Capture exit code
│    • Save raw   │  • Store raw output
│      output     │  • Stop container
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. PARSE        │  • Load parser module
│    • Convert    │  • Map to standard schema
│      to         │  • Extract findings
│      standard   │  • Calculate severity
│      format     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. STORE        │  • Update tasks table
│    • Status:    │  • Save structured JSON
│      completed  │  • Record metrics
│    • Write to   │  • Audit log entry
│      database   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 8. NOTIFY       │  • SSE event: complete
│    • Send       │  • Update UI
│      completion │  • Enable export
│      event      │
└─────────────────┘

                  Error Path
                      │
                      ▼
              ┌──────────────┐
              │ FAILED       │  • Log error
              │ • Status:    │  • Clean up
              │   failed     │  • Notify user
              │ • Store      │
              │   error msg  │
              └──────────────┘

                  Cancel Path
                      │
                      ▼
              ┌──────────────┐
              │ CANCELLED    │  • Kill process
              │ • Status:    │  • Stop container
              │   cancelled  │  • Partial results
              └──────────────┘
```

### 12.4 Data Model ER Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                     DATABASE SCHEMA                           │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐
│ plugins             │
│─────────────────────│
│ • id (PK)           │◄─────────┐
│ • name              │          │
│ • version           │          │ Foreign Key
│ • category          │          │
│ • metadata_json     │          │
│ • enabled           │          │
│ • checksum          │          │
│ • signature         │          │
│ • installed_at      │          │
└─────────────────────┘          │
                                 │
┌─────────────────────┐          │
│ tasks               │          │
│─────────────────────│          │
│ • id (PK)           │          │
│ • plugin_id (FK)────┼──────────┘
│ • tool_name         │
│ • target            │ ◄─── indexed
│ • inputs_json       │
│ • preset            │
│ • status            │ ◄─── indexed
│ • consent_granted   │
│ • safe_mode         │
│ • created_at        │ ◄─── indexed
│ • started_at        │
│ • completed_at      │
│ • duration_seconds  │
│ • exit_code         │
│ • structured_json   │
│ • raw_output_path   │
│ • error_message     │
│ • container_id      │
│ • cpu_seconds       │
│ • memory_peak_mb    │
└─────────────────────┘
         │
         │
         │ Referenced by
         │
         ▼
┌─────────────────────┐
│ audit_log           │
│─────────────────────│
│ • id (PK, auto)     │
│ • timestamp         │ ◄─── indexed
│ • event_type        │ ◄─── indexed
│ • severity          │
│ • user_id           │
│ • ip_address        │
│ • message           │
│ • context_json      │
│ • task_id (FK)──────┼─────► tasks.id
│ • plugin_id         │
└─────────────────────┘

┌─────────────────────┐          ┌─────────────────────┐
│ settings            │          │ presets             │
│─────────────────────│          │─────────────────────│
│ • key (PK)          │          │ • id (PK)           │
│ • value             │          │ • name              │
│ • type              │          │ • plugin_id (FK)────┼──► plugins.id
│ • description       │          │ • config_json       │
│ • updated_at        │          │ • created_at        │
└─────────────────────┘          │ • last_used         │
                                 │ • use_count         │
                                 └─────────────────────┘

Relationships:
• plugins 1──N tasks (one plugin, many tasks)
• tasks 1──N audit_log (one task, many audit events)
• plugins 1──N presets (one plugin, many custom presets)

Indexes:
• tasks(created_at DESC) — Recent task queries
• tasks(target) — Search by target
• tasks(status) — Filter by status
• audit_log(timestamp DESC) — Recent events
• audit_log(event_type) — Filter by event type
```

### 12.5 Consent and Sandbox Control Loop

```
┌─────────────────────────────────────────────────────────────────┐
│               SAFETY & CONSENT CONTROL FLOW                      │
└─────────────────────────────────────────────────────────────────┘

User initiates scan
        │
        ▼
┌──────────────────┐
│ Check global     │
│ consent checkbox │
└────────┬─────────┘
         │
    ┌────▼────┐
    │Checked? │
    └────┬────┘
         │
    NO ◄─┼─► YES
     │        │
     ▼        ▼
┌─────────┐ ┌──────────────────┐
│ Block   │ │ Check plugin     │
│ Disable │ │ safety_level     │
│ Start   │ └────────┬─────────┘
└─────────┘          │
              ┌──────┼──────┐
              │      │      │
        "safe"│      │"intrusive"/"exploit"
              │      │
              ▼      ▼
       ┌───────┐  ┌─────────────────────┐
       │Proceed│  │ Show High-Risk Modal│
       │       │  │ • Warning message   │
       │       │  │ • Type confirmation │
       │       │  └──────────┬──────────┘
       │       │             │
       │       │        ┌────▼─────┐
       │       │        │Confirmed?│
       │       │        └────┬─────┘
       │       │             │
       │       │        YES◄─┼─►NO
       │       │         │       │
       └───┬───┘         │       ▼
           │◄────────────┘  ┌─────────┐
           │                │ Cancel  │
           ▼                └─────────┘
┌────────────────────┐
│ Validate target    │
│ • Check whitelist  │
│ • Apply safe_mode  │
│   restrictions     │
└──────────┬─────────┘
           │
      ┌────▼────┐
      │ Valid?  │
      └────┬────┘
           │
      NO ◄─┼─► YES
       │        │
       ▼        ▼
┌─────────┐  ┌────────────────────┐
│ Show    │  │ Check rate limits  │
│ Error   │  │ • Per-tool limits  │
│ Message │  │ • Global limits    │
└─────────┘  └──────────┬─────────┘
                        │
                   ┌────▼────┐
                   │Allowed? │
                   └────┬────┘
                        │
                   NO ◄─┼─► YES
                    │        │
                    ▼        ▼
             ┌─────────┐  ┌────────────────────┐
             │ Show    │  │ Create sandbox     │
             │ Rate    │  │ • Docker container │
             │ Limit   │  │ • Resource limits  │
             │ Error   │  │ • Network isolation│
             └─────────┘  └──────────┬─────────┘
                                     │
                                     ▼
                          ┌────────────────────┐
                          │ Execute scan       │
                          │ • Monitor output   │
                          │ • Enforce timeout  │
                          │ • Log all actions  │
                          └──────────┬─────────┘
                                     │
                                     ▼
                          ┌────────────────────┐
                          │ Record audit trail │
                          │ • Consent flag     │
                          │ • Target           │
                          │ • Timestamp        │
                          │ • User context     │
                          └────────────────────┘
```

---

## 13. Appendix

### 13.1 Glossary

| Term | Definition |
|------|------------|
| **CIDR** | Classless Inter-Domain Routing notation for IP ranges (e.g., 192.168.1.0/24) |
| **Container** | Isolated execution environment using OS-level virtualization |
| **CVE** | Common Vulnerabilities and Exposures identifier |
| **CVSS** | Common Vulnerability Scoring System (0-10 scale) |
| **Pentesting** | Penetration testing—authorized security assessment |
| **Plugin** | Modular tool integration following SecuScan's metadata schema |
| **Preset** | Predefined configuration template for a tool |
| **Safe Mode** | Conservative scanning mode with rate limits and restrictions |
| **Sandbox** | Isolated execution environment preventing system access |
| **SAN** | Subject Alternative Name (SSL certificate field) |
| **SSE** | Server-Sent Events (HTTP streaming protocol) |
| **TLS** | Transport Layer Security (cryptographic protocol) |

### 13.2 Command Reference

#### CLI Commands

```bash
# Start server
secuscan serve --bind 127.0.0.1:8080

# List plugins
secuscan plugin list

# Install plugin
secuscan plugin install nmap

# Run scan (CLI mode)
secuscan scan --plugin nmap --target 192.168.1.1 --preset quick

# View task history
secuscan tasks list --limit 10

# Export report
secuscan report --task-id <uuid> --format pdf --output report.pdf

# Generate authentication token
secuscan auth generate --expires 30d

# Clean old data
secuscan clean --older-than 30d

# Database backup
secuscan db backup --output backup.db
```

### 13.3 API Quick Reference

```
GET    /health                    — Server status
GET    /plugins                   — List plugins
GET    /plugin/{id}/schema        — Plugin details
POST   /task/start                — Start scan
GET    /task/{id}/status          — Task status
GET    /task/{id}/stream          — SSE updates
GET    /task/{id}/result          — Get results
POST   /task/{id}/cancel          — Cancel task
GET    /tasks                     — List tasks
DELETE /task/{id}                 — Delete task
GET    /reports/{id}?format=pdf   — Export report
GET    /settings                  — Get settings
POST   /settings                  — Update settings
```

### 13.4 Environment Variables

```bash
SECUSCAN_DB=/path/to/secuscan.db           # Database location
SECUSCAN_BIND=127.0.0.1:8080               # Server bind address
SECUSCAN_PLUGINS_DIR=/path/to/plugins      # Plugin directory
SECUSCAN_DATA_DIR=/path/to/data            # Data storage
SECUSCAN_SAFE_MODE=true                    # Default safe mode
SECUSCAN_MAX_CONCURRENT=3                  # Max concurrent tasks
SECUSCAN_DOCKER_ENABLED=true               # Enable Docker sandbox
SECUSCAN_LOG_LEVEL=INFO                    # Logging level
SECUSCAN_AUTH_REQUIRED=false               # Enable authentication
```

### 13.5 Troubleshooting

#### Issue: "Docker not available"

**Solution:**
```bash
# Verify Docker installation
docker --version

# Check Docker daemon
docker ps

# If not running, start Docker
sudo systemctl start docker  # Linux
open -a Docker              # macOS
```

#### Issue: "Rate limit exceeded"

**Solution:**
```bash
# Check current limits
secuscan settings get rate_limits

# Temporarily increase (not recommended for production)
secuscan settings set max_tasks_per_hour 100
```

#### Issue: "Plugin signature verification failed"

**Solution:**
```bash
# Import official GPG key
gpg --import secuscan-official.asc

# Disable signature verification (dev only)
secuscan plugin install --no-verify plugin.tar.gz
```

### 13.6 Security Best Practices

1. **Never disable Safe Mode** unless you fully understand the risks
2. **Always obtain written authorization** before scanning external systems
3. **Keep plugins updated** to latest versions
4. **Review audit logs** regularly for suspicious activity
5. **Use Docker sandbox** for all scans when possible
6. **Rotate credentials** stored in vault every 90 days
7. **Enable authentication** if remote access is required
8. **Backup database** before major updates
9. **Monitor resource usage** to prevent DoS
10. **Report security issues** to security@secuscan.local

### 13.7 Contributing

SecuScan welcomes community contributions. See `CONTRIBUTING.md` for:
- Code style guidelines
- Plugin development guide
- Pull request process
- Testing requirements

### 13.8 License & Legal

**License:** MIT (see `LICENSE` file)

**Legal Notice:** SecuScan is provided for educational and authorized security testing purposes. Misuse may violate computer crime laws. Users are solely responsible for ensuring they have proper authorization before scanning any systems.

### 13.9 Support & Resources

- **Documentation:** https://docs.secuscan.local
- **Community Forum:** https://community.secuscan.local
- **GitHub Issues:** https://github.com/secuscan/secuscan/issues
- **Security Issues:** security@secuscan.local (PGP: 1234 5678 90AB)

---

**End of Document**

*SecuScan — Empowering Ethical Security Education*

*Version 1.0 | October 2025 | Confidential Internal Release*
