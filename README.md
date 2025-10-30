SecuScan — Local-First Pentesting Toolkit
Final Detailed Product Specification, October 2025
***Document Version: 1.0  
Classification: Internal Release  
Target Audience: Engineering Team, Security Researchers, Pentesting Students  
Last Updated: October 29, 2025  
***Table of Contents
Executive Summary
Tool Catalogue Overview
UI and UX Architecture
Plugin Metadata System
Backend API Contract
Standardized Output Schema
Database and Storage Layout
Sandboxing and Security Layer
UX, Legal, and Learning Tools
Packaging and Installation
Testing and CI
Visual Layout and Architecture Diagrams
Appendix
***1. Executive Summary
1.1 Product Vision
SecuScan is a local-first penetration testing platform designed to democratize security education while maintaining the highest standards of safety and ethical practice. Built on the principle that learning security should never compromise security, SecuScan operates entirely on the user's machine, eliminating the risks associated with cloud-based vulnerability scanning services and providing complete data sovereignty.
1.2 Target Personas
SecuScan serves two distinct but complementary user groups:
Persona A: The Learning Pentester
Profile: Computer science students, cybersecurity certification candidates, self-taught security enthusiasts
Needs: Structured workflows, guided experiences, clear explanations, low-risk experimentation environments
Pain Points: Overwhelmed by command-line complexity, afraid of accidentally targeting production systems, lacks confidence in tool configuration
SecuScan Solution: GUI-first experience with preset configurations, inline educational content, mandatory consent workflows, and sandbox-only execution by default
Persona B: The Power User
Profile: Professional penetration testers, security researchers, DevSecOps engineers
Needs: Scriptable automation, CLI access, customizable workflows, batch processing capabilities
Pain Points: GUI tools lack flexibility, cloud services raise data sovereignty concerns, existing tools scattered across multiple systems
SecuScan Solution: Full CLI access sharing the same preset library, API-driven automation, plugin extensibility, and composable workflows
1.3 Core Product Attributes
SecuScan is built on five foundational principles:
| Attribute | Description | Implementation |
|-----------|-------------|----------------|
| Local-First | Zero external dependencies, complete offline operation | All services run on 127.0.0.1, SQLite for persistence |
| Safety-by-Default | Prevent accidental harm through technical controls | Docker sandboxing, consent modals, rate limiting |
| Educational | Teaching tool first, professional tool second | Learning mode, inline help, narrated workflows |
| Extensible | Plugin architecture for community contributions | JSON metadata system, standardized API contracts |
| Dual-Interface | Support both GUI learners and CLI power users | Shared preset library, unified backend |
1.4 Product Purpose
Mission Statement:  
"Enable learning-driven, ethical penetration testing for academic and self-training use without exposing external systems or requiring a remote backend."
SecuScan bridges the gap between theoretical security knowledge and practical application. Students can safely experiment with professional-grade tools in controlled environments, while experienced practitioners benefit from a unified, privacy-respecting toolkit that doesn't send scan data to third-party services.
1.5 Major System Components
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
1.6 Key Differentiators
vs. Kali Linux:  
SecuScan provides a curated, guided experience rather than a comprehensive toolkit. It's designed for learning specific workflows, not replacing a full penetration testing OS.
vs. Burp Suite:  
While Burp focuses on web application proxying and manual testing, SecuScan emphasizes automated scanning workflows with educational scaffolding.
vs. Cloud Scanning Services (Qualys, Rapid7):  
Complete data privacy—no scan results leave your machine. No subscription fees, no internet requirement, no compliance concerns.
1.7 Success Metrics
Educational Impact: Users successfully complete guided pentesting workflows without external assistance
Safety Record: Zero accidental scans of unauthorized targets
Adoption: 1,000+ active users in first 6 months post-launch
Plugin Ecosystem: 10+ community-contributed plugins within first year
User Satisfaction: 4.5+ star rating on educational value
***2. Tool Catalogue Overview
2.1 Evolution Philosophy
SecuScan's tool ecosystem follows a three-phase rollout strategy, prioritizing safety, educational value, and practical utility in that order. Each phase introduces tools with progressively higher risk profiles, accompanied by proportionally stronger safeguards.
Phase 1 (MVP)          Phase 2 (Expansion)      Phase 3 (Advanced)
───────────────        ────────────────────     ──────────────────
Network Recon    ──►   Subdomain Discovery ──►  Memory Forensics
Web Inspection   ──►   Injection Testing   ──►  Exploit Frameworks
Certificate Check──►   Secret Detection    ──►  Password Recovery
                       Code Analysis
2.2 MVP Tools (Phase 1)
The initial release includes five battle-tested tools, selected for their utility in foundational penetration testing workflows and relative safety when properly configured.
***2.2.1 Nmap (Network Mapper)
Tool ID: nmap  
Binary: nmap (+ python-nmap wrapper)  
Category: Network Discovery & Port Scanning  
Purpose
Nmap performs host discovery, port enumeration, service version detection, and OS fingerprinting. It's the industry standard for network reconnaissance and forms the foundation of most penetration testing engagements.
UI Configuration Fields
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| target | string | ✓ | — | IP address, CIDR range, or hostname |
| preset | enum | ✗ | quick | Predefined scan profile |
| ports | string | ✗ | preset-dependent | Port specification (22,80,443 or 1-1000) |
| scan_type | enum | ✗ | syn | SYN/Connect/UDP scan mode |
| timeout | integer | ✗ | 300 | Maximum scan duration (seconds) |
| threads | integer | ✗ | 4 | Parallel scan threads |
| safe_mode | boolean | ✗ | true | Enable conservative timing/rate limits |
Preset Configurations
| Preset Name | Description | Parameters | Risk Level |
|-------------|-------------|------------|------------|
| Quick Host Check | Ping scan + top 100 ports | --top-ports 100 -T3 | Low |
| Top 1000 Ports | Common service discovery | --top-ports 1000 -T3 | Low |
| Service Fingerprint | Deep version detection | -sV -sC --top-ports 1000 -T4 | Medium |
| Comprehensive Scan | Full port range + scripts | -p- -sV -sC -T4 | High ⚠️ |
Output Structure
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
Safety Controls
Localhost Restriction: By default, only accepts 127.0.0.1, localhost, or 192.168.x.x targets
Aggressive Scan Protection: Timing templates T4/T5 require explicit consent modal
Rate Limiting: Maximum 10 scans per hour unless safe_mode disabled
Audit Logging: All scan commands logged with timestamp and user consent flag
***2.2.2 HTTP Inspector
Tool ID: http_inspector  
Library: requests / httpx  
Category: Web Reconnaissance  
Purpose
Performs safe, read-only HTTP requests to validate endpoint availability, examine response headers, trace redirections, and inspect TLS configurations. Ideal for initial web target profiling without active exploitation attempts.
UI Configuration Fields
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| url | string | ✓ | — | Target URL (http/https) |
| follow_redirects | boolean | ✗ | true | Follow 3xx redirect chains |
| timeout | integer | ✗ | 10 | Request timeout (seconds) |
| verify_ssl | boolean | ✗ | true | Validate TLS certificates |
| custom_headers | object | ✗ | {} | Key-value header pairs |
| method | enum | ✗ | GET | HTTP method (GET/HEAD/OPTIONS) |
Preset Configurations
| Preset Name | Parameters | Use Case |
|-------------|------------|----------|
| Quick Fetch | follow_redirects=false, timeout=5 | Fast availability check |
| Security Headers | method=HEAD, extract_headers=[security-related] | Header analysis |
| Full Inspection | All options enabled | Comprehensive endpoint profile |
Output Structure
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
Risk Level
Low — Read-only operations, no injection attempts, no authentication bypass testing.
***2.2.3 Directory Discovery
Tool ID: dir_brute  
Engine: Custom Python (asyncio + httpx)  
Category: Web Enumeration  
Purpose
Discovers hidden directories, files, and endpoints by testing common naming patterns against a target web application. Uses wordlists to systematically probe for unlinked resources that may contain sensitive information or administrative interfaces.
UI Configuration Fields
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| base_url | string | ✓ | — | Root URL to scan |
| wordlist | enum/file | ✗ | small | Predefined list or custom upload |
| extensions | string | ✗ | "" | Comma-separated extensions (.php,.html) |
| threads | integer | ✗ | 8 | Concurrent request workers |
| delay_ms | integer | ✗ | 50 | Milliseconds between requests |
| match_codes | string | ✗ | 200,301,302,403 | HTTP codes to report |
| recursive | boolean | ✗ | false | Scan discovered directories |
| max_depth | integer | ✗ | 2 | Recursion depth limit |
Preset Configurations
| Preset | Wordlist Size | Threads | Delay | Use Case |
|--------|---------------|---------|-------|----------|
| Quick Discovery | Small (500 entries) | 6 | 100ms | Fast, polite scan |
| Standard Scan | Medium (5,000 entries) | 8 | 50ms | Balanced approach |
| Deep Discovery | Large (50,000 entries) | 12 | 10ms | Comprehensive (Advanced) ⚠️ |
Wordlist Specifications
| List Name | Entries | Source | Contents |
|-----------|---------|--------|----------|
| small | 500 | Custom curated | Common directories (admin, api, backup, config, etc.) |
| medium | 5,000 | SecLists (filtered) | Web content + CMS patterns |
| large | 50,000 | Combined sources | Comprehensive discovery dictionary |
Output Structure
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
Safety Controls
Default Rate Limiting: 50ms delays prevent server overload
Consent Required: Deep scans require explicit confirmation
Auto-Throttling: Reduce speed on 429 (Too Many Requests) responses
Blacklist Protection: Blocks scans against common production domains (unless explicitly overridden)
Request Cap: Maximum 100,000 requests per scan
***2.2.4 Nikto/Wapiti (Web Passive Scanner)
Tool ID: web_passive_scan  
Binary: nikto / wapiti  
Category: Web Vulnerability Assessment  
Purpose
Automated scanner for common web server misconfigurations, outdated software versions, dangerous HTTP methods, missing security headers, and known vulnerabilities. Operates in two modes: passive (read-only) and active (includes low-risk probes).
UI Configuration Fields
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| target | string | ✓ | — | Web application URL |
| preset | enum | ✗ | passive | Scan intensity level |
| timeout | integer | ✗ | 600 | Maximum scan duration |
| safe_mode | boolean | ✗ | true | Disable intrusive checks |
| check_categories | array | ✗ | [all] | Specific test categories |
Preset Configurations
| Preset | Description | Checks Included | Risk |
|--------|-------------|-----------------|------|
| Passive Health | Read-only analysis | Headers, versions, banner grabbing | Low |
| Standard Scan | Low-risk probes | + Common paths, methods, configs | Low-Medium |
| Active Assessment | Includes exploit checks | + SQL/XSS probes, auth bypass attempts | Medium-High ⚠️ |
Check Categories
Headers: Security headers analysis (HSTS, CSP, X-Frame-Options)
SSL/TLS: Certificate validation, cipher strength, protocol versions
Methods: Dangerous HTTP methods (PUT, DELETE, TRACE)
Paths: Sensitive files (.git, .env, backup files)
Versions: Outdated software detection
Injections: SQL/XSS/Command injection (active mode only)
Output Structure
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
Safety Controls
Safe Mode Enforcement: Disables exploit attempts by default
Consent Modal: Active scans display warning and require acknowledgment
Session Isolation: Each scan runs in isolated Docker container
Result Sanitization: Removes potentially executable payloads from reports
***2.2.5 TLS / Certificate Inspector
Tool ID: tls_inspect  
Library: ssl / cryptography  
Category: Transport Security Analysis  
Purpose
Examines TLS/SSL configurations, certificate validity, cipher suites, and protocol versions. Identifies weak cryptographic implementations, expired certificates, and misconfigured trust chains without performing any active exploitation.
UI Configuration Fields
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| host | string | ✓ | — | Hostname:port (e.g., example.com:443) |
| show_chain | boolean | ✗ | true | Display full certificate chain |
| timeout | integer | ✗ | 10 | Connection timeout |
| check_ciphers | boolean | ✗ | true | Test supported cipher suites |
| check_protocols | boolean | ✗ | true | Test TLS protocol versions |
Output Structure
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
Risk Level
Minimal — Passive observation only, no modification attempts.
***2.3 Phase-2 Tools (Planned)
The following tools will be added in subsequent releases, following the same safety-first architecture:
2.3.1 Subdomain Discovery
Tools: amass, subfinder, DNS brute-forcing
Purpose: Enumerate subdomains for attack surface mapping
Safety: Rate-limited DNS queries, passive sources prioritized
2.3.2 SQLMap Integration
Tool: sqlmap
Purpose: Automated SQL injection detection and exploitation
Safety: Requires explicit consent, runs in isolated container, read-only by default
2.3.3 Nuclei Template Scanner
Tool: nuclei
Purpose: Template-based vulnerability detection
Safety: Curated template library, severity filtering
2.3.4 Scapy Packet Analyzer
Tool: scapy
Purpose: Custom packet crafting and network analysis
Safety: Localhost-only by default, raw socket permissions restricted
2.3.5 Secret Detection
Tools: detect-secrets, gitleaks
Purpose: Scan codebases for exposed credentials
Safety: File-only scanning, no network access
2.3.6 Static Code Analysis
Tools: bandit (Python), semgrep (multi-language)
Purpose: Identify code-level security vulnerabilities
Safety: Read-only file analysis
2.3.7 SSH Command Runner
Purpose: Execute commands on remote systems via SSH
Safety: Requires explicit credential storage, audit logging, command whitelisting
***2.4 Phase-3 Tools (Advanced)
High-risk tools requiring mature safety frameworks:
2.4.1 Binary Analysis
Tools: YARA, PE analyzers
Purpose: Malware analysis and binary reverse engineering
Safety: Sandboxed execution, VM-in-VM isolation
2.4.2 Memory Forensics
Tool: volatility
Purpose: Memory dump analysis
Safety: File-only, no live system access
2.4.3 Metasploit Bridge
Tool: msfconsole connector
Purpose: Exploit framework integration
Safety: Docker-only, requires advanced consent, audit logging
2.4.4 Password Recovery
Tool: hashcat
Purpose: Hash cracking for security testing
Safety: GPU isolation, local hash files only
***3. UI and UX Architecture
3.1 Deployment Model
SecuScan runs as a single-page web application (SPA) served from a local Python backend. The entire application stack operates on 127.0.0.1, eliminating network exposure risks.
Access URL: http://127.0.0.1:8080  
Backend API: http://127.0.0.1:8080/api/v1  
3.2 Visual Layout
The interface follows a dashboard-style layout optimized for both learning and productivity:
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
3.3 Component Breakdown
3.3.1 Header
Brand Identity: SecuScan logo and version number
Connection Status: Real-time backend health indicator (green dot = online)
Settings Menu: Access to global configurations (network binding, sandbox preferences, theme)
3.3.2 Left Sidebar (Tool Navigator)
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
3.3.3 Main Canvas
Top Section: Quick Scan Card
Single-input scan initiation for beginners
Target field with validation (highlights invalid IPs/URLs)
Preset dropdown populated from plugin metadata
Safe Mode toggle (large, prominent)
Start button (disabled until consent checkbox checked)
Middle-Left: Dynamic Tool Configuration
Form fields auto-generated from selected plugin's JSON metadata
Collapsible "Advanced Options" section for power users
Field validation with real-time error messages
Preset selector that auto-populates fields
"Save as Custom Preset" button
Middle-Right: Live Output Panel
Tabbed interface: Live Log | Structured Results | Raw Output
Live Log: Streaming text output with syntax highlighting
Structured Results: Formatted tables/cards based on tool type
Raw Output: Plaintext dump for copy-paste
Action buttons: Copy to Clipboard, Save to File, Clear
Auto-scroll toggle
Bottom Section: Task History
Card-based layout showing recent scans
Each card displays:
Task ID (clickable to load full results)
Tool name and icon
Target address
Status badge (Running/Completed/Failed/Cancelled)
Timestamp
Actions: View Results, Re-run, Export, Delete
Pagination controls (10/25/50 per page)
Filter by tool, date range, or status
3.3.4 Footer
Legal Notice: "SecuScan is for authorized testing only. Unauthorized scanning may be illegal."
Consent Checkbox: Required for all scan initiations
Version Info: Current release and update availability
3.4 Interaction Flow
Standard Scan Workflow
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
Technical Flow
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
3.5 Responsive Design
While SecuScan is optimized for desktop use (minimum 1280x800), the interface gracefully adapts:
Desktop (1920x1080+): Full layout with split panels
Laptop (1280x800): Sidebar collapsible, stacked panels
Tablet (768x1024): Sidebar hidden by default, single-column layout
Mobile: Not officially supported (CLI recommended for mobile/tablet users)
3.6 Accessibility
Keyboard Navigation: Full tab-order support, Ctrl+K command palette
Screen Reader: ARIA labels on all interactive elements
Color Contrast: WCAG AA compliance (4.5:1 minimum)
High Contrast Mode: Toggle in settings for visual impairment
Reduced Motion: Respects prefers-reduced-motion system setting
***4. Plugin Metadata System
4.1 Architecture Philosophy
SecuScan's plugin system treats tools as declarative configurations rather than hardcoded integrations. Each tool is defined by a JSON metadata file that describes its interface, capabilities, and safety characteristics. The backend dynamically loads these files at startup, enabling:
Zero-Code Tool Addition: Add new tools without modifying backend code
UI Auto-Generation: Forms, help text, and validation rules derived from metadata
Consistent Behavior: All tools follow the same execution and reporting patterns
Community Extensions: Third-party plugins can be verified and installed
4.2 Metadata Schema
Full Schema Definition
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
4.3 Field Type Reference
| Type | UI Control | Validation | Example |
|------|-----------|------------|---------|
| string | Text input | Regex pattern | 192.168.1.1 |
| text | Textarea | Length limits | Multi-line config |
| integer | Number input | Min/max range | 1-65535 |
| boolean | Toggle switch | N/A | true/false |
| select | Dropdown | Options list | quick/standard/deep |
| multiselect | Checkbox group | Options list | [ssh, http, ftp] |
| file | File upload | Extension filter | .txt, .csv |
| keyvalue | Key-value table | JSON schema | {"User-Agent": "..."} |
4.4 Command Template Syntax
The command_template field supports conditional logic and variable substitution:
Syntax Elements:
{variable}                    → Direct substitution
{variable:default_value}      → Use default if variable empty
--if:condition:then:A:else:B  → Conditional insertion
--each:list:template          → Iterate over array
Examples:
[
  "nmap",
  "-sV",
  "{target}",
  "--if:safe_mode:then:-T3:else:-T4",
  "--if:ports:then:-p {ports}",
  "--each:scripts:then:--script {item}"
]
Rendered with {target: "192.168.1.1", safe_mode: true, ports: "80,443"}:
nmap -sV 192.168.1.1 -T3 -p 80,443
4.5 Parser System
Plugins can specify how their output should be parsed:
Built-in Parsers
| Parser ID | Format | Tools |
|-----------|--------|-------|
| builtin_nmap | Nmap XML | Nmap scans |
| builtin_nikto | Nikto CSV | Nikto/Wapiti |
| builtin_json | JSON | Custom scripts |
| builtin_xml | Generic XML | Various |
| builtin_regex | Regex extraction | Log parsers |
Custom Parsers
Plugins can provide Python parser scripts:
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
4.6 Plugin Loading and Validation
Load Sequence
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
Validation Rules
Schema Compliance: Must match JSON schema definition
Unique ID: No duplicate plugin IDs
Binary Existence: Check binary paths if engine=cli
Docker Image: Verify image availability if engine=docker
Safety Classification: Valid safety level
Signature (Optional): Valid GPG signature from trusted key
4.7 Plugin Directory Structure
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
***5. Backend API Contract
5.1 API Versioning
Base URL: http://127.0.0.1:8080/api/v1  
Protocol: REST over HTTP  
Serialization: JSON  
Authentication: Token-based (optional, disabled by default)  
5.2 Endpoint Reference
5.2.1 Health & Status
GET /health
Returns backend operational status and system information.
Request:
GET /api/v1/health HTTP/1.1
Host: 127.0.0.1:8080
Response:
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
***5.2.2 Plugin Management
GET /plugins
Lists all available plugins with metadata summary.
Request:
GET /api/v1/plugins HTTP/1.1
Response:
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
***GET /plugin/{id}/schema
Returns full plugin metadata including field definitions and presets.
Request:
GET /api/v1/plugin/nmap/schema HTTP/1.1
Response:
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
***GET /presets
Returns all preset configurations aggregated across plugins.
Response:
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
***5.2.3 Task Execution
POST /task/start
Initiates a new plugin execution task.
Request:
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
Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "created_at": "2025-10-29T14:20:30Z",
  "stream_url": "/api/v1/task/550e8400-e29b-41d4-a716-446655440000/stream"
}
Error Response (400):
{
  "error": "validation_failed",
  "message": "Target field is required",
  "field": "target"
}
***GET /task/{id}/status
Returns current task status.
Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 45,
  "started_at": "2025-10-29T14:20:35Z",
  "elapsed_seconds": 12
}
Status Values:
queued — Waiting for execution slot
running — Currently executing
completed — Finished successfully
failed — Execution error
cancelled — User-terminated
***GET /task/{id}/stream
Server-Sent Events stream for real-time updates.
Response (SSE):
event: log
data: {"timestamp": "14:20:35", "message": "Starting Nmap scan..."}
event: progress
data: {"percent": 25, "current": "Scanning port 80"}
event: log
data: {"timestamp": "14:20:40", "message": "Found open port: 22/tcp"}
event: complete
data: {"status": "completed", "duration": 8.2}
***GET /task/{id}/result
Returns standardized scan results.
Response:
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
***POST /task/cancel
Terminates a running task.
Request:
POST /api/v1/task/550e8400-e29b-41d4-a716-446655440000/cancel HTTP/1.1
Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled",
  "cancelled_at": "2025-10-29T14:21:00Z"
}
***5.2.4 Task Management
GET /tasks
Lists all tasks with pagination and filtering.
Query Parameters:
page (int, default=1)
per_page (int, default=25, max=100)
plugin_id (string, optional)
status (enum, optional)
date_from (ISO8601, optional)
date_to (ISO8601, optional)
Request:
GET /api/v1/tasks?page=1&per_page=25&plugin_id=nmap&status=completed HTTP/1.1
Response:
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
***DELETE /task/{id}
Deletes a task and its associated data.
Response:
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "deleted": true
}
***5.2.5 Reports & Export
GET /reports/{id}
Downloads task results in specified format.
Query Parameters:
format (enum: json|csv|pdf)
Request:
GET /api/v1/reports/550e8400-e29b-41d4-a716-446655440000?format=pdf HTTP/1.1
Response:
HTTP/1.1 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="nmap_scan_20251029_142030.pdf"
[PDF binary data]
***5.2.6 Settings
GET /settings
Returns current global settings.
Response:
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
***POST /settings
Updates global settings.
Request:
{
  "safety": {
    "safe_mode_default": false
  }
}
Response:
{
  "updated": true,
  "settings": {...}
}
***5.3 Authentication
By default, SecuScan runs without authentication (localhost-only binding is the security boundary). Optional token-based auth can be enabled:
Header:
Authorization: Bearer <token>
Tokens generated via:
secuscan auth generate --expires 30d
***5.4 Rate Limiting
Global Limits:
100 requests/minute per client
50 task starts per hour
3 concurrent running tasks
Response Headers:
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1698595200
Rate Limit Response (429):
{
  "error": "rate_limit_exceeded",
  "message": "Maximum 50 tasks per hour allowed",
  "retry_after": 1800
}
***6. Standardized Output Schema
6.1 Unified Result Format
All plugins produce output conforming to a standardized schema, enabling consistent UI rendering, export formats, and result aggregation.
6.2 Core Schema
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
6.3 Tool-Specific Structured Formats
6.3.1 Nmap Output
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
6.3.2 HTTP Inspector Output
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
6.3.3 Directory Discovery Output
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
6.3.4 Web Scanner (Nikto) Output
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
6.3.5 TLS Inspector Output
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
6.4 Severity Classification
Findings are categorized using industry-standard severity levels:
| Level | Description | CVSS Range | UI Color |
|-------|-------------|------------|----------|
| Critical | Immediate exploitation risk, requires urgent action | 9.0-10.0 | Red |
| High | Significant security weakness, high priority | 7.0-8.9 | Orange |
| Medium | Moderate risk, should be addressed | 4.0-6.9 | Yellow |
| Low | Minor issue, low exploitation likelihood | 0.1-3.9 | Blue |
| Info | Informational finding, no direct risk | 0.0 | Gray |
***7. Database and Storage Layout
7.1 Database Technology
Engine: SQLite 3.35+  
Location: $HOME/.secuscan/secuscan.db  
Encryption: Optional (SQLCipher extension)  
Backup: Automatic daily snapshots to $HOME/.secuscan/backups/  
7.2 Database Schema
Table: tasks
Stores all scan task records and their execution state.
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
Table: plugins
Plugin registry and configuration.
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
Table: settings
Global application configuration.
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
Table: audit_log
Security audit trail for compliance and forensics.
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
Table: presets
User-defined custom presets (supplements plugin defaults).
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
7.3 Filesystem Storage
Directory Structure
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
File Rotation and Cleanup
Raw Outputs:
Retained for 30 days by default
Configurable retention period: 7/30/90/365 days or indefinite
Manual cleanup via UI or secuscan clean --older-than 30d
Database Backups:
Daily snapshots at 2 AM local time
Retained for 7 days (configurable)
Compressed with gzip to save space
Logs:
Rotated daily
Maximum 10 MB per log file
Compressed older than 7 days
Retained for 30 days
7.4 Data Export Formats
JSON Export
Full structured export including all metadata:
{
  "task": {...},
  "results": {...},
  "metadata": {...}
}
CSV Export
Flattened results suitable for spreadsheet import:
Task ID,Plugin,Target,Timestamp,Status,Duration,Finding Type,Severity,Description
...
PDF Export
Professional report format:
Executive summary
Methodology
Findings table with severity color-coding
Detailed results
Recommendations
Technical appendix
***8. Sandboxing and Security Layer
8.1 Defense-in-Depth Architecture
SecuScan implements multiple overlapping security controls to prevent accidental harm, unauthorized access, and data exfiltration.
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
8.2 Network Isolation
Localhost-Only Binding
Default Configuration:
network:
  bind_address: "127.0.0.1"
  bind_port: 8080
  allow_remote_access: false
Enforcement:
Backend server validates bind address on startup
Refuses to start if 0.0.0.0 binding attempted without explicit override
Warning message displayed if remote access enabled
Firewall-Friendly
SecuScan requires no inbound connections, making it compatible with restrictive firewall policies.
8.3 Docker Sandbox Execution
Every scan runs in an isolated Docker container with strict resource limits and capability restrictions.
Container Configuration
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
Runtime Security
Filesystem:
Root filesystem read-only
/tmp writable but memory-backed (ephemeral)
Output directory mounted with write-only permissions
Plugin directory mounted read-only
Network:
Bridge network with egress filtering
DNS resolution allowed
HTTP/HTTPS allowed for web tools
Raw sockets restricted to specific tools
Processes:
Single process per container
Automatic termination after timeout
No shell access
PID namespace isolation
8.4 Namespace Isolation (Fallback)
If Docker is unavailable, SecuScan falls back to Linux namespace isolation:
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
Limitations:
Less isolation than Docker
Requires root or specific capabilities
Recommended for development/testing only
8.5 Plugin Verification
Whitelist System
Trusted Plugin Registry:
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
Verification Process
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
8.6 Input Validation
Target Address Filtering
Allowed by Default:
127.0.0.1, localhost, ::1
Private IP ranges: 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12
Explicit hostnames (if user confirms)
Blocked by Default:
Public IP ranges (unless safe mode disabled)
Known cloud provi
