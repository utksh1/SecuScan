# SecuScan — Local-First Pentesting Toolkit
## Final Detailed Product Specification, October 2025

**Document Version:** 1.0  
**Last Updated:** October 29, 2025  
**Classification:** Internal / Educational Use  
**License:** MIT (Planned)

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

---

# 1. Executive Summary

## 1.1 Introduction

**SecuScan** is a local-first penetration testing platform designed to democratize cybersecurity education while maintaining the highest standards of safety, ethics, and usability. Built for students, educators, and security professionals, SecuScan operates entirely on the user's machine, eliminating the risks associated with cloud-based security tools and external attack surfaces.

In an era where cybersecurity skills are in critical demand, SecuScan bridges the gap between theoretical knowledge and practical application. It provides a controlled, sandbox-first environment where users can learn ethical hacking techniques, conduct security assessments, and understand vulnerability detection—all without the risk of accidental damage to production systems or legal complications.

## 1.2 Target Personas

### Persona 1: The Learning Pentester

**Profile:**
- Students enrolled in cybersecurity programs
- Self-taught security enthusiasts
- IT professionals transitioning to security roles
- Individuals preparing for certifications (CEH, OSCP, etc.)

**Needs:**
- Guided workflows with clear explanations
- Safe, controlled testing environments
- Visual feedback and structured reports
- Educational context for each tool and technique
- Low barrier to entry with minimal setup

**Pain Points:**
- Fear of breaking things or triggering security alerts
- Overwhelming complexity of traditional pentesting tools
- Lack of clear learning paths in existing tools
- Difficulty interpreting raw tool outputs

### Persona 2: The Power User

**Profile:**
- Experienced penetration testers
- Security researchers
- Red team operators
- Bug bounty hunters

**Needs:**
- Command-line interface for automation
- Scriptable workflows and batch operations
- Advanced configuration options
- Integration with existing toolchains
- Reproducible scan configurations

**Pain Points:**
- GUI tools are too slow for repetitive tasks
- Need for consistent output formats across tools
- Difficulty maintaining scan history and reports
- Tool fragmentation across different platforms

## 1.3 Core Design Principles

### Principle 1: Local-First Architecture
**Every operation runs on the user's machine.** No data leaves the local environment unless explicitly configured. This approach ensures:
- Complete privacy and data sovereignty
- No subscription fees or cloud dependencies
- Offline operability in air-gapped environments
- Reduced latency and improved performance
- Compliance with data protection regulations

### Principle 2: Safety by Default
**Every scan is sandboxed unless explicitly disabled.** SecuScan assumes users are learning and prioritizes safety mechanisms:
- Docker containerization for process isolation
- Rate limiting to prevent accidental DoS scenarios
- Safe mode presets enabled by default
- Explicit consent required for intrusive operations
- Localhost binding to prevent external exposure

### Principle 3: Dual Interface Philosophy
**Both GUI and CLI share the same backend and presets.** Users can:
- Start in the GUI for visual learning
- Graduate to CLI for automation and speed
- Use identical configurations across interfaces
- Export and share scan presets as JSON
- Switch contexts without relearning tool syntax

### Principle 4: Extensibility Through Plugins
**New tools integrate via standardized metadata.** The plugin system enables:
- Community-contributed tool integrations
- Custom tool wrappers for proprietary scanners
- Version-controlled tool configurations
- Signature verification for security
- Hot-reloading of plugin updates

## 1.4 System Overview

SecuScan comprises five major architectural components that work in concert to deliver a seamless pentesting experience:

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  Web GUI (React + TailwindCSS)  │  CLI (Python Click/Typer)    │
│  • Form-based tool execution     │  • Scriptable commands       │
│  • Live log streaming            │  • JSON output support       │
│  • Visual report generation      │  • Batch operations          │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI/Flask)                   │
├─────────────────────────────────────────────────────────────────┤
│  • RESTful endpoints for task management                         │
│  • Server-Sent Events for real-time updates                     │
│  • Input validation and sanitization                            │
│  • Authentication and rate limiting                             │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER (Python)                   │
├─────────────────────────────────────────────────────────────────┤
│  • Plugin loader and metadata parser                            │
│  • Task queue and execution manager                             │
│  • Result parser and normalizer                                 │
│  • Report generator and exporter                                │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION LAYER (Docker)                     │
├─────────────────────────────────────────────────────────────────┤
│  • Containerized tool execution                                 │
│  • Resource limits (CPU, memory, network)                       │
│  • Read-only filesystem mounts                                  │
│  • Network isolation and filtering                              │
└─────────────────────────────────────────────────────────────────┘
                                 ↓
┌─────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER (SQLite)                     │
├─────────────────────────────────────────────────────────────────┤
│  • Task history and metadata                                    │
│  • Plugin configurations                                        │
│  • User settings and preferences                                │
│  • Audit logs and compliance records                            │
└─────────────────────────────────────────────────────────────────┘
```

### Technology Stack Summary

| Layer | Primary Technology | Alternatives Considered |
|-------|-------------------|------------------------|
| **Frontend** | React 18+ with TypeScript | Vue.js, Svelte |
| **Styling** | TailwindCSS + shadcn/ui | Material-UI, Ant Design |
| **Backend API** | FastAPI (Python 3.10+) | Flask, Django REST |
| **Task Queue** | Celery with Redis | RQ, Dramatiq |
| **Database** | SQLite 3.35+ | PostgreSQL (future) |
| **Containerization** | Docker 24+ | Podman compatible |
| **CLI Framework** | Click or Typer | argparse, docopt |
| **Icons** | Lucide React | Heroicons, Feather |

## 1.5 Mission Statement

> **"Enable learning-driven, ethical penetration testing for academic and self-training use without exposing external systems or requiring a remote backend."**

SecuScan exists to make cybersecurity education accessible, safe, and practical. By providing a professional-grade toolkit with educational guardrails, we empower the next generation of security professionals to develop real-world skills in a controlled environment.

## 1.6 Key Differentiators

### vs. Kali Linux / ParrotOS
- **Lighter weight:** Single application vs. full OS distribution
- **Beginner friendly:** Guided workflows vs. expert-only tools
- **Modern UI:** Web-based interface vs. terminal-only
- **Sandboxed by default:** Automatic isolation vs. manual configuration

### vs. Burp Suite / OWASP ZAP
- **Broader scope:** Network + web + forensics vs. web-only
- **Local-first:** No cloud components vs. cloud sync features
- **Educational focus:** Learning modes vs. professional-only
- **Open plugin system:** Community extensible vs. proprietary plugins

### vs. Metasploit Framework
- **Safety-first:** Sandboxed execution vs. raw exploitation
- **Accessibility:** GUI + CLI vs. CLI-only
- **Learning curves:** Graduated complexity vs. steep learning curve
- **Modern stack:** Python/JavaScript vs. Ruby legacy

## 1.7 Success Metrics

**User Adoption Metrics:**
- Monthly active users (MAU)
- User retention rate (30-day, 90-day)
- CLI vs. GUI usage ratio
- Average scans per user per week

**Educational Impact:**
- Time to first successful scan
- Progression from safe to advanced modes
- Documentation page views
- Community tutorial contributions

**Technical Performance:**
- Scan completion success rate
- Average scan duration by tool
- Docker overhead vs. native execution
- API response times (p50, p95, p99)

**Ecosystem Growth:**
- Community-contributed plugins
- Third-party integrations
- Educational institution adoptions
- Bug bounty program participation

---

# 2. Tool Catalogue Overview

## 2.1 Tool Ecosystem Philosophy

SecuScan's tool catalogue is organized around a **progressive disclosure model**—beginners start with safe, passive reconnaissance tools while advanced users can unlock intrusive testing capabilities. Each tool is carefully selected based on:

1. **Educational value:** Does it teach fundamental pentesting concepts?
2. **Safety profile:** Can it be safely containerized and rate-limited?
3. **Output parsability:** Can results be standardized for reporting?
4. **Community adoption:** Is it widely used in the security industry?
5. **Maintenance burden:** Is it actively developed and documented?

### Tool Maturity Stages

```
MVP Tools (Phase 1)          Phase-2 Tools              Phase-3 Tools
┌─────────────────┐         ┌─────────────────┐       ┌─────────────────┐
│ • Safe by default│         │ • Consent required│      │ • Expert mode   │
│ • Always enabled │         │ • Docker enforced │      │ • High consent  │
│ • Quick presets  │         │ • Advanced UI     │      │ • Audit logging │
└─────────────────┘         └─────────────────┘       └─────────────────┘
     ↓                              ↓                          ↓
  Nmap, HTTP              SQLMap, Subdomain         Metasploit, Volatility
  Inspector, TLS          Discovery, Nuclei         YARA, Hashcat
```

## 2.2 MVP Tools (Initial Implementation)

These tools form the foundation of SecuScan v0.1 and are optimized for safety and education.

---

### 2.2.1 Nmap — Network Mapper

**Category:** Network Discovery  
**Safety Level:** Safe (with rate limits)  
**Container Required:** Recommended  
**Skill Level:** Beginner to Advanced

#### Purpose Statement
Nmap is the industry-standard tool for network discovery and security auditing. SecuScan wraps Nmap to provide host discovery, port scanning, service detection, and OS fingerprinting in a safe, controlled manner.

#### UI Field Configuration

| Field Name | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string | ✅ Yes | — | IP address, CIDR range, or hostname |
| `preset` | enum | ❌ No | `quick` | Pre-configured scan profiles |
| `ports` | string | ❌ No | `top100` | Port specification (80,443 or 1-1000) |
| `scan_type` | enum | ❌ No | `syn` | TCP SYN, TCP Connect, or UDP |
| `timeout` | integer | ❌ No | 300 | Maximum scan duration (seconds) |
| `threads` | integer | ❌ No | 4 | Parallel scanning threads |
| `safe_mode` | boolean | ❌ No | `true` | Enable rate limiting and stealth options |

#### Default Presets

**Quick Host Check:**
- Preset: `quick`
- Ports: Top 100
- Use case: Initial reconnaissance to identify live hosts
- Duration: ~60 seconds

**Service Fingerprint:**
- Preset: `service_fingerprint`
- Ports: Top 1000
- Safe mode: `false` (requires consent)
- Use case: Identify outdated or vulnerable service versions
- Duration: ~5 minutes

**Full TCP Scan:**
- Preset: `full`
- Ports: 1-65535
- Requires: Explicit user consent
- Use case: Thorough enumeration for red team assessments
- Duration: ~30 minutes

#### Output Structure
- Host list with status (up/down)
- Open ports with service names and versions
- Operating system detection results
- Summary statistics (total hosts, open ports, scan duration)

#### Safety Mechanisms
- Force localhost binding by default
- Require consent for non-safe/fast scans
- Rate limiting: Maximum 10 packets per second in safe mode
- Target validation: Block sensitive IP ranges without authorization

---

### 2.2.2 HTTP Inspector

**Category:** Web Reconnaissance  
**Safety Level:** Safe  
**Container Required:** No  
**Skill Level:** Beginner

#### Purpose Statement
Validates URL availability, analyzes HTTP headers, and traces redirect chains. Non-invasive tool for understanding web server configurations and security header analysis.

#### UI Field Configuration

| Field Name | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `url` | string (URL) | ✅ Yes | — | Target URL with scheme (http:// or https://) |
| `follow_redirects` | boolean | ❌ No | `true` | Follow 3xx redirects |
| `timeout` | integer | ❌ No | 10 | Request timeout in seconds |
| `custom_headers` | key-value | ❌ No | `{}` | Additional request headers (advanced) |

#### Default Presets

**Quick Fetch:**
- Follow redirects: `false`
- Timeout: 5 seconds
- Use case: Verify if URL is accessible

**Security Header Audit:**
- Method: HEAD
- Follow redirects: `true`
- Use case: Check for missing security headers (HSTS, CSP, etc.)

#### Output Structure
- HTTP status code and reason
- Response headers table
- Set-Cookie analysis with security flags
- Redirect chain visualization
- TLS certificate details (issuer, expiry, cipher)

#### Risk Level
**Minimal** - Only performs read operations, no data sent to target beyond standard HTTP requests.

---

### 2.2.3 Directory Discovery (dir_brute)

**Category:** Web Enumeration  
**Safety Level:** Moderate (rate-limited)  
**Container Required:** Recommended  
**Skill Level:** Intermediate

#### Purpose Statement
Brute-force discovery of hidden directories, files, and endpoints on web servers using wordlists. Essential for finding admin panels, backup files, and undocumented APIs.

#### UI Field Configuration

| Field Name | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `base_url` | string (URL) | ✅ Yes | — | Target base URL |
| `wordlist` | enum | ❌ No | `small` | small, medium, large, or upload custom |
| `extensions` | string (CSV) | ❌ No | — | File extensions (.php,.bak,.zip) |
| `threads` | integer | ❌ No | 8 | Concurrent request threads |
| `delay_ms` | integer | ❌ No | 50 | Delay between requests (milliseconds) |

#### Default Presets

**Quick:**
- Wordlist: Small (1,000 entries)
- Delay: 100ms
- Threads: 6
- Use case: Initial recon to find obvious exposed resources

**Deep:**
- Wordlist: Large (100,000 entries)
- Delay: 10ms
- Threads: 12
- Safe mode: `false` (requires advanced consent)
- Use case: Thorough assessment for penetration tests

#### Output Structure
- Found endpoints with full URLs
- HTTP status codes and content lengths
- Content-type headers
- Response time measurements
- Severity categorization (critical, high, medium, low)

#### Safety Mechanisms
- Default rate-limiting (50ms delay)
- Automatic pause on 429 (Too Many Requests)
- Target validation and baseline requests
- False positive filtering for custom 404 pages

---

### 2.2.4 Nikto/Wapiti (web_passive_scan)

**Category:** Web Application Security  
**Safety Level:** Moderate to High  
**Container Required:** Yes (enforced)  
**Skill Level:** Intermediate to Advanced

#### Purpose Statement
Automated detection of common web server misconfigurations, weak security headers, outdated software versions, and known vulnerability patterns.

#### UI Field Configuration

| Field Name | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `target` | string (URL) | ✅ Yes | — | Target web application URL |
| `preset` | enum | ❌ No | `passive` | passive, active |
| `timeout` | integer | ❌ No | 600 | Maximum scan duration (seconds) |
| `safe_mode` | boolean | ❌ No | `true` | Enable passive-only checks |

#### Default Presets

**Passive Health Check:**
- Mode: Passive
- Safe mode: `true`
- Use case: Non-intrusive reconnaissance for misconfigurations

**Active Vulnerability Scan:**
- Mode: Active
- Safe mode: `false`
- Requires: Explicit consent and authorization proof
- Use case: Comprehensive vulnerability assessment

#### Output Structure
- Categorized findings by security area:
  - Missing security headers
  - Information disclosure
  - Outdated software versions
  - Default files and directories
  - Known CVE matches
- Risk ratings (High, Medium, Low, Info)
- Remediation recommendations

#### Risk Assessment
- **Passive scans:** Safe for any authorized target
- **Active scans:** May trigger security alerts and IDS/IPS systems
- Consent modal required for active mode

---

### 2.2.5 TLS / Certificate Inspector (tls_inspect)

**Category:** Cryptography & Compliance  
**Safety Level:** Safe  
**Container Required:** No  
**Skill Level:** Beginner

#### Purpose Statement
Analyzes TLS/SSL certificate chains, validates expiry dates, checks cipher suite support, and identifies common SSL/TLS misconfigurations.

#### UI Field Configuration

| Field Name | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `host` | string | ✅ Yes | — | Hostname and port (example.com:443) |
| `show_chain` | boolean | ❌ No | `true` | Display full certificate chain |
| `timeout` | integer | ❌ No | 10 | Connection timeout (seconds) |

#### Output Structure
- **Certificate Information:**
  - Subject and issuer details
  - Validity period (not before / not after)
  - Days until expiration
  - Serial number and signature algorithm
  - Subject Alternative Names (SANs)
  
- **Chain Validation:**
  - Full certificate chain display
  - Trust validation status
  - Intermediate certificate presence
  
- **Security Analysis:**
  - Supported TLS versions (TLS 1.0, 1.1, 1.2, 1.3)
  - Cipher suite enumeration
  - Weak cipher detection
  - Certificate revocation status (OCSP)
  - Vulnerabilities (Heartbleed, POODLE, etc.)

#### Output Warnings
- Certificate expiring within 30 days
- Self-signed certificates
- Weak signature algorithms (MD5, SHA-1)
- Support for deprecated TLS versions
- Missing intermediate certificates

#### Risk Level
**Minimal** - Read-only TLS handshake analysis with no data transmission.

---

## 2.3 Phase-2 Tools (Next Additions)

These tools will be added in subsequent releases, inheriting the same plugin architecture and safety mechanisms:

### Subdomain Discovery (amass/subfinder)
- **Purpose:** Enumerate subdomains using passive DNS sources
- **Safety:** Passive-only by default (no active DNS queries)
- **Output:** List of discovered subdomains with sources

### SQLMap (Automated SQL Injection)
- **Purpose:** Detect and exploit SQL injection vulnerabilities
- **Safety:** High-risk tool requiring explicit consent
- **Container:** Enforced with network isolation
- **Output:** Vulnerable parameters, DBMS fingerprint, extracted data

### Nuclei (Template-Based Scanner)
- **Purpose:** Run community-maintained vulnerability templates
- **Safety:** Template risk rating system
- **Output:** CVE matches, misconfigurations, exposed services

### Scapy (Packet Crafting)
- **Purpose:** Custom packet generation and network probing
- **Safety:** Expert-only mode with audit logging
- **Output:** Packet captures and response analysis

### Secret Scanners (detect-secrets / Gitleaks)
- **Purpose:** Scan source code and repositories for leaked credentials
- **Safety:** Local filesystem only
- **Output:** Found secrets with line numbers and entropy scores

### Code Analyzers (Bandit / Semgrep)
- **Purpose:** Static analysis for security vulnerabilities in code
- **Safety:** Read-only file access
- **Output:** Vulnerability patterns with CWE mappings

### SSH Runner
- **Purpose:** Controlled remote command execution over SSH
- **Safety:** User-provided credentials, command whitelisting
- **Output:** Command results and connection logs

---

## 2.4 Phase-3 Tools (Forensics and Exploit Frameworks)

Advanced tools for expert users, requiring highest consent level and full Docker isolation:

### YARA / PE Inspector
- **Purpose:** Binary analysis and pattern matching for malware detection
- **Use case:** Reverse engineering and malware analysis

### Volatility (Memory Forensics)
- **Purpose:** Analyze memory dumps for artifacts and IOCs
- **Use case:** Incident response and forensics training

### Metasploit Connector
- **Purpose:** Sandboxed exploitation framework integration
- **Safety:** Fully isolated containers, logged exploits

### Hashcat Interface
- **Purpose:** GPU-accelerated password recovery
- **Use case:** Password audit and recovery training

**All Phase-3 tools:**
- Require expert mode activation
- Enforce Docker containerization
- Log all operations to audit trail
- Display prominent legal disclaimers
- Support only local/lab targets

---

# 3. UI and UX Architecture

## 3.1 Application Delivery Model

SecuScan runs as a **single-page application (SPA)** served locally at `http://127.0.0.1:8080` (configurable port). The web-based interface combines the accessibility of modern web design with the security of local-only execution.

### Why Web-Based?

**Cross-platform consistency:**
- Identical experience on macOS, Linux, and Windows
- No platform-specific UI code to maintain
- Browser rendering handles font, layout, and accessibility

**Modern development ecosystem:**
- React + TypeScript for type-safe components
- TailwindCSS for rapid, consistent styling
- Rich component libraries (shadcn/ui)
- Chrome DevTools for debugging

**Future extensibility:**
- Easy to add dashboards and visualizations
- WebSocket/SSE support for real-time updates
- Potential for browser extensions
- Progressive Web App (PWA) capabilities

## 3.2 Layout Structure

```
┌──────────────────────────────────────────────────────────────────┐
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ HEADER                                                     │   │
│ │ SecuScan Logo | Server Status: ● Online | ⚙️ Settings     │   │
│ └────────────────────────────────────────────────────────────┘   │
├──────────┬───────────────────────────────────────────────────────┤
│          │                                                        │
│ SIDEBAR  │              MAIN CANVAS                              │
│          │                                                        │
│ Network  │  ┌────────────────────────────────────────────┐       │
│  • Nmap  │  │ QUICK SCAN CARD                            │       │
│  • Ping  │  │ Target: [_______________] [Scan Type: ▼]  │       │
│          │  │ [Start Scan] 🛡️ Safe Mode: ON             │       │
│ Web      │  └────────────────────────────────────────────┘       │
│  • HTTP  │                                                        │
│  • Dir   │  ┌──────────────┬─────────────────────────────┐       │
│  • Nikto │  │ FIELD FORM   │ LIVE OUTPUT                 │       │
│          │  │              │                             │       │
│ Crypto   │  │ URL:         │ [2025-10-29 19:35:22]      │       │
│  • TLS   │  │ [__________] │ Starting HTTP Inspector...  │       │
│          │  │              │ Target: example.com         │       │
│ Tools    │  │ Timeout:     │ Status: 200 OK              │       │
│  • Tasks │  │ [10] seconds │ Headers received (12)       │       │
│  • Export│  │              │ TLS: Valid (Let's Encrypt) │       │
│          │  │ [Advanced ▼] │ ✓ Scan complete             │       │
│          │  │              │ [Copy] [Save] [Clear]       │       │
│          │  └──────────────┴─────────────────────────────┘       │
│          │                                                        │
│          │  ┌────────────────────────────────────────────┐       │
│          │  │ TASK HISTORY                               │       │
│          │  │ ┌────────────────────────────────────────┐ │       │
│          │  │ │ #1234 • Nmap • 192.168.1.0/24          │ │       │
│          │  │ │ Status: ✓ Complete • 42s • 12 hosts    │ │       │
│          │  │ │ [View] [Export] [Rerun]                │ │       │
│          │  │ └────────────────────────────────────────┘ │       │
│          │  └────────────────────────────────────────────┘       │
├──────────┴───────────────────────────────────────────────────────┤
│ FOOTER                                                            │
│ ⚖️ For authorized testing only | ☑️ I accept responsibility     │
└──────────────────────────────────────────────────────────────────┘
```

## 3.3 Component Breakdown

### Header Bar
- **Logo and Title:** "SecuScan" with version number
- **Server Status Indicator:** Green (connected), Yellow (degraded), Red (disconnected)
- **Settings Icon:** Configuration modal access

### Left Sidebar (Tool Navigator)
Organized by security domain:
- 📡 Network (Nmap, Ping Sweep, Traceroute)
- 🌐 Web Applications (HTTP Inspector, Directory Discovery, Nikto, TLS)
- 🔍 Reconnaissance (Subdomain Discovery, WHOIS, DNS)
- 💻 Code Analysis (Secret Scanner, Bandit, Semgrep)
- 📊 Utilities (Task Manager, Report Generator, Export Center)

### Quick Scan Card
One-click access to common scenarios with large target input, preset dropdown, and Safe Mode toggle.

### Dynamic Field Form
Auto-generated from plugin metadata with real-time validation and help tooltips.

### Live Output Panel
Real-time streaming logs with copy/save/clear controls, progress indicators, and structured results view.

### Task History Cards
Persistent record showing task ID, tool, target, status, duration, and action buttons (View, Export, Rerun, Delete).

### Footer Bar
Legal notice, consent checkbox (required for execution), and quick links to documentation.

## 3.4 Interaction Flow

```
User arrives → Check consent → Select tool → Generate form →
Fill parameters → Validate → Start scan → POST /api/task/start →
Backend creates task → Establish SSE connection → Execute in Docker →
Stream progress → Parse results → Display output → Add to history →
Enable exports
```

## 3.5 Responsive Design

- **Desktop (1920x1080+):** Three-column layout
- **Laptop (1366x768):** Collapsible sidebar, two-column layout
- **Tablet (768x1024):** Single column, tabbed navigation
- **Mobile:** CLI recommended (minimal support in v1.0)

## 3.6 Accessibility Features

- WCAG 2.1 AA compliance goals
- Semantic HTML5 with ARIA labels
- Keyboard navigation (Tab, Enter, Esc)
- Screen reader support
- Minimum 4.5:1 contrast ratio
- Keyboard shortcuts (Ctrl+K for search, Ctrl+Enter to scan)

## 3.7 Theme System

- **Light Mode:** Clean white background, dark text
- **Dark Mode:** Dark gray (#1a1a1a), reduced eye strain
- **High Contrast Mode:** Pure black/white for accessibility

---

# 4. Plugin Metadata System

## 4.1 Philosophy

The plugin system is SecuScan's **architectural cornerstone**. Each tool is defined by a **declarative JSON metadata file** describing inputs, outputs, execution method, and safety profile.

### Core Principles:
1. **Declarative over Imperative**
2. **Validation-First**
3. **Backwards Compatible**
4. **Security-Centric**
5. **UI-Agnostic** (powers both GUI and CLI)

## 4.2 Plugin Metadata Schema

Located at `plugins/{tool_id}/metadata.json`:

```json
{
  "schema_version": "1.0",
  "plugin": {
    "id": "nmap",
    "name": "Nmap Network Scanner",
    "version": "1.0.0",
    "author": "SecuScan Team",
    "description": "Industry-standard network discovery tool",
    "category": "network",
    "tags": ["port-scan", "service-detection"],
    "icon": "network-wired",
    "documentation_url": "https://nmap.org/book/man.html"
  },
  "execution": {
    "engine": "cli",
    "command_template": [
      "nmap", "{{scan_type}}", "-p", "{{ports}}",
      "{{target}}", "--max-retries", "{{timeout}}"
    ],
    "timeout_seconds": 600,
    "container": {
      "required": true,
      "image": "instrumentisto/nmap:latest",
      "memory_limit": "512m",
      "cpu_limit": "2.0"
    }
  },
  "fields": [
    {
      "id": "target",
      "label": "Target",
      "type": "string",
      "required": true,
      "validation": {
        "pattern": "^(\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}|[a-zA-Z0-9.-]+)$"
      }
    },
    {
      "id": "preset",
      "label": "Scan Preset",
      "type": "enum",
      "options": [
        {"value": "quick", "label": "Quick Scan"},
        {"value": "full", "label": "Full Scan"}
      ]
    }
  ],
  "presets": {
    "quick": {
      "parameters": {
        "ports": "top100",
        "scan_type": "-sS",
        "safe_mode": true
      },
      "safety_level": "safe"
    }
  },
  "safety": {
    "level": "safe",
    "consent_required_if": {"field": "safe_mode", "equals": false}
  }
}
```

## 4.3 Field Type Reference

| Type | UI Component | Validation |
|------|--------------|------------|
| `string` | Text input | Regex pattern |
| `integer` | Number input | Min/max range |
| `boolean` | Toggle switch | None |
| `enum` | Dropdown select | Option whitelist |
| `array` | Tag input | Item validation |
| `keyvalue` | Key-value editor | Key/value patterns |
| `file` | File picker | Extension whitelist |
| `ipaddress` | Text input | IP format check |
| `url` | Text input | URL format check |

## 4.4 Dynamic Form Generation

The UI automatically generates input forms from plugin metadata:

1. Read `fields` array from metadata
2. Render appropriate component based on `type`
3. Apply validation rules
4. Show/hide fields based on conditional logic
5. Set defaults and display help text

## 4.5 Preset System

Presets are **named parameter bundles** for common use cases:
- Lower barrier to entry for beginners
- Consistent scan configurations
- Shareable across team members
- User can create custom presets

## 4.6 Safety Level Definitions

| Level | Consent | Docker | Examples |
|-------|---------|--------|----------|
| `safe` | None | Recommended | HTTP Inspector, TLS Check |
| `intrusive` | Modal | Required | Nmap aggressive, Dir brute |
| `exploit` | Double-confirm | Enforced | SQLMap, Metasploit |
| `destructive` | Triple-confirm | Enforced | File deletion |

## 4.7 Plugin Versioning

- **Format:** Semantic Versioning (MAJOR.MINOR.PATCH)
- **Updates:** Daily background checks with user approval
- **Rollback:** Old versions retained for compatibility

---

# 5. Backend API Contract

## 5.1 API Design Principles

SecuScan's REST API follows modern best practices:
- **RESTful conventions** for resource naming
- **JSON** for all request/response bodies
- **Server-Sent Events (SSE)** for real-time updates
- **Versioned endpoints** for backwards compatibility
- **Idempotent operations** where applicable

## 5.2 Core Endpoints

### System Health and Information

#### GET `/api/health`
**Purpose:** Backend health check and server information

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0-beta",
  "uptime_seconds": 86400,
  "active_tasks": 3,
  "queue_depth": 1,
  "docker_available": true,
  "plugins_loaded": 8
}
```

#### GET `/api/version`
**Purpose:** Detailed version information

**Response:**
```json
{
  "version": "0.1.0-beta",
  "build_date": "2025-10-29",
  "commit_hash": "a1b2c3d",
  "python_version": "3.10.12",
  "docker_version": "24.0.5"
}
```

---

### Plugin Management

#### GET `/api/plugins`
**Purpose:** List all available plugins with metadata

**Query Parameters:**
- `category` (optional): Filter by category (network, web, etc.)
- `safety_level` (optional): Filter by safety level

**Response:**
```json
{
  "plugins": [
    {
      "id": "nmap",
      "name": "Nmap Network Scanner",
      "category": "network",
      "version": "1.0.0",
      "safety_level": "safe",
      "description": "Industry-standard network discovery tool",
      "icon": "network-wired"
    }
  ],
  "total": 8
}
```

#### GET `/api/plugins/{plugin_id}/schema`
**Purpose:** Get detailed plugin configuration schema

**Response:**
```json
{
  "plugin_id": "nmap",
  "fields": [...],
  "presets": {...},
  "execution": {...},
  "safety": {...}
}
```

#### GET `/api/presets`
**Purpose:** Get all available presets across all plugins

**Response:**
```json
{
  "presets": {
    "nmap": {
      "quick": {...},
      "service": {...}
    },
    "http_inspector": {
      "quick_fetch": {...}
    }
  }
}
```

---

### Task Execution

#### POST `/api/tasks/start`
**Purpose:** Start a new scan task

**Request Body:**
```json
{
  "plugin_id": "nmap",
  "parameters": {
    "target": "192.168.1.0/24",
    "preset": "quick",
    "safe_mode": true
  },
  "consent_acknowledged": true
}
```

**Response:**
```json
{
  "task_id": "task_1730227515_abc123",
  "status": "queued",
  "created_at": "2025-10-29T19:35:15Z",
  "estimated_duration_seconds": 60,
  "sse_url": "/api/tasks/task_1730227515_abc123/stream"
}
```

**Status Codes:**
- `201 Created`: Task successfully queued
- `400 Bad Request`: Invalid parameters
- `403 Forbidden`: Consent not acknowledged
- `429 Too Many Requests`: Rate limit exceeded

#### POST `/api/tasks/{task_id}/cancel`
**Purpose:** Cancel a running task

**Response:**
```json
{
  "task_id": "task_1730227515_abc123",
  "status": "cancelled",
  "cancelled_at": "2025-10-29T19:36:00Z"
}
```

#### GET `/api/tasks/{task_id}/status`
**Purpose:** Get current task status

**Response:**
```json
{
  "task_id": "task_1730227515_abc123",
  "status": "running",
  "progress_percent": 45,
  "current_operation": "Scanning port 443/tcp",
  "started_at": "2025-10-29T19:35:20Z",
  "elapsed_seconds": 25
}
```

**Status Values:**
- `queued`: Waiting to execute
- `running`: Currently executing
- `completed`: Finished successfully
- `failed`: Execution error
- `cancelled`: User cancelled
- `timeout`: Exceeded time limit

#### GET `/api/tasks/{task_id}/stream`
**Purpose:** Server-Sent Events stream for real-time updates

**SSE Event Types:**
- `status`: Status change events
- `log`: Log line output
- `progress`: Progress updates
- `result`: Final result (when complete)
- `error`: Error messages

**Example Events:**
```
event: status
data: {"status": "running", "progress": 10}

event: log
data: {"timestamp": "2025-10-29T19:35:22Z", "message": "Starting scan..."}

event: progress
data: {"percent": 45, "current": "Scanning 192.168.1.50"}

event: result
data: {"status": "completed", "summary": {...}}
```

#### GET `/api/tasks/{task_id}/result`
**Purpose:** Get complete task results (only after completion)

**Response:** See Section 6 for detailed output schema

---

### Task Management

#### GET `/api/tasks`
**Purpose:** List all tasks with pagination and filtering

**Query Parameters:**
- `status` (optional): Filter by status
- `plugin_id` (optional): Filter by plugin
- `page` (default: 1): Page number
- `per_page` (default: 20): Results per page
- `sort` (default: created_at): Sort field
- `order` (default: desc): Sort order (asc/desc)

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "task_1730227515_abc123",
      "plugin_id": "nmap",
      "plugin_name": "Nmap Network Scanner",
      "target": "192.168.1.0/24",
      "status": "completed",
      "created_at": "2025-10-29T19:35:15Z",
      "completed_at": "2025-10-29T19:36:00Z",
      "duration_seconds": 45,
      "findings_count": 12
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 156,
    "total_pages": 8
  }
}
```

#### DELETE `/api/tasks/{task_id}`
**Purpose:** Delete a task and its results

**Response:**
```json
{
  "deleted": true,
  "task_id": "task_1730227515_abc123"
}
```

---

### Export and Reporting

#### GET `/api/tasks/{task_id}/export`
**Purpose:** Export task results in various formats

**Query Parameters:**
- `format` (required): json, csv, pdf, html

**Response:**
- `application/json` for JSON
- `text/csv` for CSV
- `application/pdf` for PDF
- `text/html` for HTML

#### POST `/api/reports/generate`
**Purpose:** Generate multi-task report

**Request Body:**
```json
{
  "task_ids": ["task_123", "task_456"],
  "format": "pdf",
  "include_raw_output": false,
  "template": "executive_summary"
}
```

**Response:**
```json
{
  "report_id": "report_abc123",
  "download_url": "/api/reports/report_abc123/download",
  "expires_at": "2025-11-05T19:35:15Z"
}
```

#### GET `/api/reports/{report_id}/download`
**Purpose:** Download generated report

---

### Settings and Configuration

#### GET `/api/settings`
**Purpose:** Get current application settings

**Response:**
```json
{
  "bind_address": "127.0.0.1",
  "bind_port": 8080,
  "docker_enabled": true,
  "sandbox_enforced": true,
  "rate_limit_enabled": true,
  "daily_consent_required": true,
  "audit_logging": true,
  "theme": "dark"
}
```

#### PUT `/api/settings`
**Purpose:** Update application settings

**Request Body:** Same structure as GET response

**Response:**
```json
{
  "updated": true,
  "restart_required": false
}
```

---

## 5.3 Authentication

**Default Mode:** No authentication required (localhost only)

**Optional Token Authentication:**
- Disabled by default
- Can be enabled in settings for remote access scenarios
- Bearer token in Authorization header
- Tokens generated via CLI: `secuscan auth generate-token`

**Example:**
```
Authorization: Bearer secuscan_token_a1b2c3d4e5f6
```

---

## 5.4 Rate Limiting

**Per-IP Limits:**
- 100 requests per minute for GET endpoints
- 20 requests per minute for POST endpoints
- 5 concurrent task executions per user

**Response Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1730227600
```

**429 Response:**
```json
{
  "error": "Rate limit exceeded",
  "retry_after_seconds": 45
}
```

---

## 5.5 Error Handling

**Standard Error Response:**
```json
{
  "error": {
    "code": "INVALID_TARGET",
    "message": "Target must be valid IP, CIDR, or hostname",
    "details": {
      "field": "target",
      "provided_value": "invalid!@#"
    }
  },
  "request_id": "req_abc123"
}
```

**HTTP Status Codes:**
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing/invalid authentication
- `403 Forbidden`: Consent not provided
- `404 Not Found`: Resource doesn't exist
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation failed
- `429 Too Many Requests`: Rate limited
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Docker/backend unavailable

---

# 6. Standardized Output Schema

## 6.1 Output Design Philosophy

All plugin executions produce a **unified JSON structure** regardless of the underlying tool. This standardization enables:
- Consistent report generation
- Cross-tool correlation
- Simplified UI rendering
- Database indexing and search
- API client predictability

## 6.2 Universal Result Schema

```json
{
  "task_id": "task_1730227515_abc123",
  "plugin_id": "nmap",
  "plugin_name": "Nmap Network Scanner",
  "plugin_version": "1.0.0",
  "execution": {
    "started_at": "2025-10-29T19:35:15Z",
    "completed_at": "2025-10-29T19:36:00Z",
    "duration_seconds": 45.3,
    "status": "completed",
    "exit_code": 0
  },
  "target": {
    "value": "192.168.1.0/24",
    "type": "cidr",
    "resolved_ips": ["192.168.1.1", "192.168.1.2"]
  },
  "parameters": {
    "preset": "quick",
    "safe_mode": true,
    "ports": "top100"
  },
  "summary": {
    "description": "Discovered 12 live hosts with 48 open ports",
    "severity_counts": {
      "critical": 0,
      "high": 2,
      "medium": 8,
      "low": 15,
      "info": 23
    },
    "total_findings": 48,
    "key_findings": [
      "SSH service with outdated version on 192.168.1.10",
      "HTTP service on non-standard port 8080"
    ]
  },
  "structured": {
    "hosts": [
      {
        "ip": "192.168.1.10",
        "hostname": "server01.local",
        "status": "up",
        "ports": [
          {
            "port": 22,
            "protocol": "tcp",
            "state": "open",
            "service": "ssh",
            "version": "OpenSSH 7.4",
            "cpe": "cpe:/a:openbsd:openssh:7.4",
            "severity": "high",
            "note": "Outdated SSH version with known vulnerabilities"
          }
        ]
      }
    ]
  },
  "raw": {
    "stdout": "/data/raw/task_1730227515_abc123_stdout.txt",
    "stderr": "/data/raw/task_1730227515_abc123_stderr.txt",
    "output_file": "/data/raw/task_1730227515_abc123_output.xml"
  },
  "metadata": {
    "user_agent": "SecuScan/0.1.0",
    "machine_id": "mac-12345",
    "consent_acknowledged": true,
    "sandbox_used": true,
    "docker_image": "instrumentisto/nmap:latest"
  }
}
```

## 6.3 Tool-Specific Structured Output Examples

### Nmap Structured Output
```json
"structured": {
  "scan_stats": {
    "hosts_scanned": 256,
    "hosts_up": 12,
    "hosts_down": 244,
    "total_ports_scanned": 1200,
    "open_ports": 48,
    "filtered_ports": 15,
    "closed_ports": 1137
  },
  "hosts": [...]
}
```

### HTTP Inspector Structured Output
```json
"structured": {
  "response": {
    "status_code": 200,
    "headers": {...},
    "cookies": [...],
    "redirect_chain": [...]
  },
  "security_analysis": {
    "missing_headers": ["Content-Security-Policy"],
    "insecure_cookies": [],
    "tls_issues": [],
    "score": 85
  }
}
```

### Directory Discovery Structured Output
```json
"structured": {
  "findings": [
    {
      "path": "/admin",
      "status_code": 401,
      "content_length": 1234,
      "severity": "high"
    }
  ],
  "statistics": {
    "requests_made": 1000,
    "found_paths": 23,
    "response_codes": {"200": 15, "403": 8}
  }
}
```

---

# 7. Database and Storage Layout

## 7.1 Database Choice: SQLite

**Rationale:**
- Zero configuration required
- Single-file portability
- Sufficient for expected workload (< 10K tasks)
- ACID compliance for data integrity
- Embedded (no separate server process)
- Easy backup and migration

**Future Migration Path:** PostgreSQL for enterprise deployments

## 7.2 Schema Design

### Table: `tasks`

```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    plugin_id TEXT NOT NULL,
    plugin_name TEXT NOT NULL,
    plugin_version TEXT NOT NULL,
    target TEXT NOT NULL,
    parameters JSON NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds REAL,
    exit_code INTEGER,
    structured_json JSON,
    raw_stdout_path TEXT,
    raw_stderr_path TEXT,
    raw_output_path TEXT,
    summary TEXT,
    findings_count INTEGER DEFAULT 0,
    severity_critical INTEGER DEFAULT 0,
    severity_high INTEGER DEFAULT 0,
    severity_medium INTEGER DEFAULT 0,
    severity_low INTEGER DEFAULT 0,
    severity_info INTEGER DEFAULT 0,
    consent_acknowledged BOOLEAN DEFAULT FALSE,
    sandbox_used BOOLEAN DEFAULT TRUE,
    docker_image TEXT,
    error_message TEXT
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_plugin_id ON tasks(plugin_id);
CREATE INDEX idx_tasks_target ON tasks(target);
CREATE INDEX idx_tasks_completed_at ON tasks(completed_at DESC);
```

### Table: `plugins`

```sql
CREATE TABLE plugins (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    category TEXT NOT NULL,
    metadata_json JSON NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP,
    signature_hash TEXT,
    signature_valid BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_plugins_category ON plugins(category);
CREATE INDEX idx_plugins_enabled ON plugins(enabled);
```

### Table: `settings`

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `audit_log`

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,
    user_id TEXT,
    task_id TEXT,
    plugin_id TEXT,
    action TEXT NOT NULL,
    details JSON,
    ip_address TEXT,
    user_agent TEXT
);

CREATE INDEX idx_audit_timestamp ON audit_log(timestamp DESC);
CREATE INDEX idx_audit_event_type ON audit_log(event_type);
CREATE INDEX idx_audit_task_id ON audit_log(task_id);
```

### Table: `presets`

```sql
CREATE TABLE presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    plugin_id TEXT NOT NULL,
    parameters JSON NOT NULL,
    is_builtin BOOLEAN DEFAULT FALSE,
    is_custom BOOLEAN DEFAULT FALSE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    FOREIGN KEY (plugin_id) REFERENCES plugins(id)
);

CREATE INDEX idx_presets_plugin_id ON presets(plugin_id);
```

### Table: `reports`

```sql
CREATE TABLE reports (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    format TEXT NOT NULL,
    task_ids JSON NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    download_count INTEGER DEFAULT 0
);

CREATE INDEX idx_reports_created_at ON reports(created_at DESC);
```

## 7.3 File System Structure

```
secuscan/
├── data/
│   ├── secuscan.db              # SQLite database
│   ├── raw/                      # Raw tool outputs
│   │   ├── task_123_stdout.txt
│   │   ├── task_123_stderr.txt
│   │   └── task_123_output.xml
│   ├── reports/                  # Generated reports
│   │   ├── report_abc_exec.pdf
│   │   └── report_xyz_technical.json
│   └── temp/                     # Temporary files
├── plugins/                      # Plugin metadata
│   ├── nmap/
│   │   ├── metadata.json
│   │   └── parser.py
│   ├── http_inspector/
│   │   └── metadata.json
│   └── ...
├── logs/                         # Application logs
│   ├── secuscan.log
│   ├── access.log
│   └── error.log
└── config/
    ├── settings.yaml
    ├── blocked_ips.txt
    └── allowed_networks.txt
```

## 7.4 Data Retention Policy

**Default Retention:**
- Task results: 90 days
- Audit logs: 1 year
- Reports: 30 days
- Raw outputs: 30 days

**Configurable Options:**
- Unlimited retention (disabled auto-cleanup)
- Custom retention periods per data type
- Manual cleanup via UI or CLI

**Cleanup Process:**
```sql
-- Daily cleanup job
DELETE FROM tasks 
WHERE completed_at < datetime('now', '-90 days');

DELETE FROM reports 
WHERE created_at < datetime('now', '-30 days');
```

---

# 8. Sandboxing and Security Layer

## 8.1 Defense-in-Depth Architecture

SecuScan implements **multiple layers of security** to protect both the user's system and external targets:

```
Layer 1: Input Validation
Layer 2: Authorization & Consent
Layer 3: Docker Containerization
Layer 4: Network Isolation
Layer 5: Resource Limits
Layer 6: Audit Logging
```

## 8.2 Layer 1: Input Validation

**Client-Side Validation:**
- Regex pattern matching for IPs, URLs, ports
- Type checking (string, integer, boolean)
- Range validation for numeric inputs
- Required field enforcement

**Server-Side Validation:**
- Re-validate all client inputs (never trust client)
- Sanitize for command injection
- Validate against plugin schema
- Check target against blocklist

**Validation Example:**
```python
def validate_target(target: str, allow_private: bool = False):
    # Check format
    if not is_valid_ip_or_hostname(target):
        raise ValidationError("Invalid target format")
    
    # Check blocklist
    if target in load_blocklist():
        raise ValidationError("Target is blocked")
    
    # Check for private IPs
    if not allow_private and is_private_ip(target):
        raise ValidationError("Private IPs blocked in safe mode")
    
    return target
```

## 8.3 Layer 2: Authorization & Consent

### Consent Requirement Levels

**Level 0: No Consent (Read-Only)**
- HTTP Inspector
- TLS Certificate Check
- WHOIS Lookup

**Level 1: Basic Consent (Standard Checkbox)**
- Nmap with safe mode
- Directory discovery with rate limits
- Passive vulnerability scans

**Level 2: Explicit Consent (Modal Confirmation)**
- Nmap aggressive scans
- Active vulnerability testing
- Credential testing

**Level 3: High-Risk Consent (Type Confirmation)**
- Exploitation tools
- Metasploit integration
- Destructive operations

### Consent Flow Implementation

```javascript
// Frontend consent check
async function startScan(params) {
  const consentLevel = getRequiredConsentLevel(params);
  
  if (consentLevel === 0) {
    return executeScan(params);
  }
  
  if (consentLevel === 1 && !isBasicConsentChecked()) {
    showError("Please acknowledge legal terms");
    return;
  }
  
  if (consentLevel === 2) {
    const confirmed = await showConsentModal({
      title: "Active Scanning Requires Consent",
      message: "This scan may trigger security alerts...",
      confirmText: "I Have Authorization"
    });
    if (!confirmed) return;
  }
  
  if (consentLevel === 3) {
    const typed = await showTypeConfirmModal({
      requireText: "I ACCEPT THE RISKS"
    });
    if (typed !== "I ACCEPT THE RISKS") return;
  }
  
  return executeScan({...params, consent_acknowledged: true});
}
```

## 8.4 Layer 3: Docker Containerization

**Default Configuration:**
```yaml
# Docker container settings
container:
  image: "secuscan/runner:latest"
  network_mode: "bridge"
  read_only_root: true
  security_opt:
    - "no-new-privileges:true"
    - "seccomp=default"
  cap_drop:
    - ALL
  cap_add:
    - NET_RAW      # Only if required by tool (e.g., Nmap)
  tmpfs:
    - /tmp:rw,noexec,nosuid
  memory_limit: "512m"
  cpu_limit: "2.0"
  pids_limit: 100
  ulimits:
    nofile: 1024
    nproc: 64
```

**Isolation Benefits:**
- Process isolation from host
- Filesystem protection (read-only root)
- Network segmentation
- Resource limits prevent DoS
- Easy cleanup (container removal)

**Fallback: Namespace Isolation**
If Docker unavailable, use Linux namespaces:
- PID namespace
- Network namespace
- Mount namespace
- Limited resource controls via cgroups

## 8.5 Layer 4: Network Isolation

**Localhost Binding:**
```python
# API server binds only to localhost by default
app.run(host='127.0.0.1', port=8080)
```

**Container Network Rules:**
```yaml
# Only allow outbound connections
# Block container-to-container communication
# DNS resolution allowed
# No incoming connections to container
```

**Target Validation:**
```python
BLOCKED_RANGES = [
    "0.0.0.0/8",          # Current network
    "10.0.0.0/8",         # Private (optional)
    "127.0.0.0/8",        # Loopback
    "169.254.0.0/16",     # Link-local
    "224.0.0.0/4",        # Multicast
    "240.0.0.0/4"         # Reserved
]

def is_blocked_target(target_ip):
    for blocked_range in BLOCKED_RANGES:
        if ip_in_range(target_ip, blocked_range):
            return True
    return False
```

## 8.6 Layer 5: Resource Limits

**Per-Task Limits:**
- Maximum execution time: 30 minutes (configurable)
- Maximum memory: 512 MB (configurable)
- Maximum CPU: 2 cores
- Maximum disk writes: 100 MB
- Maximum network bandwidth: 10 Mbps

**Rate Limiting:**
```python
RATE_LIMITS = {
    "tasks_per_minute": 5,
    "concurrent_tasks": 3,
    "api_requests_per_minute": 100
}
```

**Timeout Enforcement:**
```python
async def execute_task(task_id, timeout_seconds=1800):
    try:
        result = await asyncio.wait_for(
            run_plugin(task_id),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        log_error(f"Task {task_id} exceeded timeout")
        kill_container(task_id)
        return {"status": "timeout"}
```

## 8.7 Layer 6: Audit Logging

**All security-relevant events logged:**
- Task execution (start, complete, cancel)
- Consent acknowledgments
- Configuration changes
- Failed validation attempts
- Rate limit violations
- Error conditions

**Log Format:**
```json
{
  "timestamp": "2025-10-29T19:35:15Z",
  "event": "task_started",
  "task_id": "task_123",
  "plugin_id": "nmap",
  "target": "192.168.1.0/24",
  "user_ip": "127.0.0.1",
  "consent_level": 1,
  "sandbox_used": true,
  "parameters": {...}
}
```

**Log Retention:**
- Stored in database and log files
- Tamper-evident (append-only)
- Searchable via UI
- Exportable for compliance

## 8.8 Plugin Security

**Signature Verification:**
```python
def verify_plugin_signature(metadata_path):
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    expected_hash = metadata["signature"]["hash"]
    actual_hash = calculate_file_hash(metadata_path)
    
    if expected_hash != actual_hash:
        raise SecurityError("Plugin signature mismatch")
    
    # Verify GPG signature if available
    if "gpg_signature" in metadata["signature"]:
        verify_gpg_signature(metadata_path)
```

**Plugin Sandboxing:**
- Plugins cannot access filesystem outside container
- No direct network access (proxied)
- Cannot spawn arbitrary processes
- Limited to declared command templates

---


# 9. UX, Legal, and Learning Tools

## 9.1 Learning Mode

**Goal:** Provide a guided, low-risk environment for beginner pentesters to learn core concepts without damaging real systems.

- **Safe Targets Library:** Curated list of lab environments and intentionally vulnerable services hosted locally (e.g., DVWA in Docker, OWASP Juice Shop in Docker), plus synthetic endpoints (mock HTTP/TLS servers) for predictable outcomes.
- **Narrated Steps:** Inline walkthroughs explain what a tool does, why it matters, expected outcomes, and how to interpret results. Each step links to glossary entries and external docs.
- **Recipe Cards:** Scenario-based flows (e.g., “Scan a local subnet safely”, “Check web headers”, “Find hidden directories”) with one-click execution using safe presets.
- **Progressive Unlocks:** More intrusive presets remain hidden until users complete introductory recipes and acknowledge consent levels.
- **Practice Datasets:** Bundled JSON/PCAP samples to replay analysis tools without any network activity.

## 9.2 Inline Help and Context

- **Metadata-Driven Help:** Field-level help text, examples, and warnings are derived directly from plugin metadata (`fields.help`, `fields.examples`, `safety.level`).
- **Context Chips:** Small labeled chips appear next to dangerous fields (e.g., “Intrusive”, “High Traffic”), linking to a consent explainer.
- **Result Hints:** Each finding includes a short interpretation tip and a link to remediation guidance.

## 9.3 Consent UX

- **Footer Consent Checkbox:** Must be checked to enable any task execution. State persists per session; resets on app restart by default.
- **Modal Confirmations:** Triggered automatically when the required consent level for selected parameters exceeds the current consent state. See Section 8.3 for levels.
- **Typed Confirmation:** For exploit/active tools, require typing a phrase like “I ACCEPT THE RISKS” and selecting an authorized target scope.
- **Audit Binding:** The consent acceptance is embedded into the task record (`consent_acknowledged: true`) and audit log.

## 9.4 Legal Positioning and Safeguards

> SecuScan is designed for authorized, educational use only. The user bears full responsibility for complying with applicable laws and institutional policies.

- **Localhost-First:** Default target suggestions point to `127.0.0.1` and private lab networks; public IPs require an extra confirmation.
- **Institution Templates:** Optional policy pack that pre-configures blocklists, rate limits, and allowed target ranges.
- **Disclaimers:** Prominent in first-run flow, footer, and consent modals.
- **Data Handling:** All data remains on-device. Exports are opt-in and explicitly labeled with sensitivity markers.

## 9.5 Reporting and Exports

- **Formats:** JSON (raw and structured), CSV (summary), PDF/HTML (readable reports).
- **Executive Summary:** High-level overview with risk counts, top findings, and recommended next steps for non-technical readers.
- **Technical Appendix:** Full tool outputs, command templates, environment info, and version metadata for reproducibility.
- **Watermarks:** “For Educational Use” watermark in PDFs generated in Learning Mode.
- **Redaction Options:** Remove sensitive headers, tokens, or endpoints on export.

---

# 10. Packaging and Installation

## 10.1 Distribution Options

- **Docker Compose (Recommended):** `docker-compose.yml` orchestrates `gui`, `api`, and `runner` containers with a shared `data/` volume. Easiest cross-platform setup and strongest isolation.
- **Local Install Script:** `install.sh` validates Python 3.10+, Docker availability, creates a virtualenv, installs dependencies, sets up the database schema, and verifies permissions.
- **Standalone Binary (Windows):** PyInstaller build producing a self-contained executable with embedded Python runtime and a local web GUI.
- **Signed Plugin Packs:** GPG-signed tarballs published per release; GUI can verify and install offline.

## 10.2 Example docker-compose.yml (Conceptual)

```yaml
version: "3.9"
services:
  api:
    image: secuscan/api:0.1.0
    ports:
      - "127.0.0.1:8081:8081"
    volumes:
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - SECUSCAN_BIND_ADDRESS=127.0.0.1
      - SECUSCAN_BIND_PORT=8081
      - SECUSCAN_SANDBOX_ENFORCED=true
    restart: unless-stopped

  gui:
    image: secuscan/gui:0.1.0
    ports:
      - "127.0.0.1:8080:80"
    environment:
      - API_BASE_URL=http://127.0.0.1:8081/api
    depends_on:
      - api
    restart: unless-stopped

  runner:
    image: secuscan/runner:0.1.0
    volumes:
      - ./data:/runner/data
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - RUNNER_QUEUE=default
    restart: unless-stopped
```

## 10.3 Installation Flow

1. Download the release bundle or clone the repository.
2. Run `install.sh` which:
   - Checks Python and Docker versions
   - Creates `data/` directory and initializes SQLite
   - Installs Python dependencies (API/CLI)
   - Verifies Docker access and pulls base images
   - Prints next steps and local URLs
3. Launch via `docker compose up -d` or `python -m secuscan.api` and `python -m secuscan.gui` for dev mode.

## 10.4 Licensing

- **Core:** MIT License (or compatible permissive license)
- **Plugins:** Respect upstream tool licenses; metadata and wrappers are MIT, binaries follow their original licenses.
- **Third-Party Notices:** Included in `THIRD_PARTY_NOTICES.md`.

---

# 11. Testing and CI

## 11.1 Testing Strategy

- **Unit Tests:** Input validation, parameter coercion, parser correctness, safety-level routing, and consent logic.
- **Integration Tests:** End-to-end task lifecycle using mock/simulated targets, filesystem writes, and Docker execution (tagged, can be skipped locally).
- **Contract Tests:** Ensure API responses conform to OpenAPI schema; check backward compatibility for plugin metadata.
- **Performance Tests:** Measure typical scan durations and API latencies; enforce thresholds for p95.
- **Security Tests:** Static analysis for the codebase, dependency scanning, and container image scanning.
- **Metadata Linting:** Validate all plugin metadata files against JSON Schema with CI gating.

## 11.2 CI Pipeline (Conceptual)

- Trigger on PRs and main branch merges.
- Stages:
  - Lint (Python, TypeScript) and format check
  - Unit tests (API, parsers, CLI)
  - Metadata schema validation
  - Container builds (api/gui/runner)
  - Integration tests with Docker-in-Docker (select smoke tests)
  - SBOM generation and container image scan
  - Artifact publishing (signed)

## 11.3 v0.1 Roadmap (Weeks 0–4)

| Week | Milestone | Deliverables |
|------|-----------|--------------|
| 0 | Repo structure | Monorepo skeleton, `plugins/` scaffolding, basic docs |
| 1 | Plugin loader, API, executor | Metadata schema, `/api/plugins`, `/api/tasks/start`, task queue |
| 2 | Sandbox + Logging | Docker runner, consent/rate-limiting, audit log, SSE streaming |
| 3 | Parsing, Reporting, History | Normalized result schema, PDF/CSV export, task list UI |
| 4 | Packaging and tests | Docker Compose, install script, CI pipeline, smoke tests |

---

# 12. Visual Layout and Architecture Diagrams

Below are diagram prompts and ASCII placeholders. For production docs, request high-res diagrams from Gamma using these prompts.

## 12.1 System Overview (Frontend ↔ API ↔ Docker Sandbox ↔ Files)

```
[Browser SPA]
    │  HTTP/SSE
    ▼
[API Server]
    │  Task queue / Plugin loader
    ▼
[Runner] —(Docker)→ [Tool Containers]
    │                    │
    └── write results ───┘
           ▼
        [SQLite / Filesystem]
```

Gamma prompt: “System overview of a local-first pentesting toolkit where a local SPA talks to a Python API that orchestrates Dockerized tools and stores results in SQLite and the filesystem. Emphasize localhost-only arrows and sandbox boundaries.”

## 12.2 Plugin Loader Flow

```
Load metadata.json → Validate JSON Schema → Register fields/presets →
Build command template → Verify safety level → Expose via /api/plugins →
Hot-reload on change
```

Gamma prompt: “Flowchart showing plugin metadata ingestion, schema validation, command template rendering, safety verification, and API exposure.”

## 12.3 Task Lifecycle (Creation → Execution → Storage → Report)

```
Create Task → Queue → Allocate Sandbox → Execute → Stream Logs →
Parse & Normalize → Store to SQLite → Generate Summary → Export/Report
```

Gamma prompt: “Swimlane diagram with User, GUI, API, Runner, Docker, and Storage lanes visualizing the task lifecycle and SSE events.”

## 12.4 Data Model ER Diagram (SQLite)

Entities: `tasks`, `plugins`, `settings`, `audit_log`, `presets`, `reports` with relationships (`presets.plugin_id → plugins.id`).

Gamma prompt: “ER diagram for SQLite including tasks, plugins, settings, audit_log, presets, and reports with key fields and indexes.”

## 12.5 Consent and Sandbox Control Loop

```
User selects preset → Determine required consent →
If insufficient → Show modal → On accept → mark consent →
Enforce Docker sandbox → Apply rate limits → Execute → Log audit →
On violation → Abort and record incident
```

Gamma prompt: “Control loop diagram highlighting consent gates, sandbox enforcement, rate limits, and audit logging with failure paths.”

---

## Appendix A: Glossary

- **Safe Mode:** Preset configuration that rate-limits and avoids invasive operations.
- **Sandbox:** Isolated execution environment (typically a Docker container) with restricted privileges.
- **SSE:** Server-Sent Events, a uni-directional streaming protocol from server to client.
- **Preset:** Named parameter bundle for a plugin/tool.
- **Structured Output:** Normalized JSON for UI/reporting; tool-agnostic.

## Appendix B: Quickstart Commands (CLI)

```bash
# Health check
secuscan api health

# List plugins
secuscan plugins ls

# Start a safe Nmap scan
secuscan task start nmap --target 192.168.1.0/24 --preset quick --safe-mode

# Watch task logs
secuscan task logs --task-id task_123

# Export results
secuscan task export --task-id task_123 --format pdf
```

## Appendix C: Security Defaults (Summary)

- Bind address: `127.0.0.1`
- Sandbox enforced: ON
- Consent requirement: ON (modal for intrusive, typed for exploit)
- API rate limits: 100 GET/min, 20 POST/min
- Max concurrent tasks: 3
- Data retention: 90 days (tasks), 30 days (raw/reports)

