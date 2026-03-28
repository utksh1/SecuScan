# SecuScan Plugin Directory

> **22 Plugins** across 3 safety tiers — Last synced: 2026-03-25

---

## 📡 Network Reconnaissance

### 1. 🔍 Nmap — Port Scanning
**ID:** `nmap` · **Safety:** Safe · **Dependency:** `nmap`
Comprehensive network discovery and service fingerprinting.

### 2. 🌍 Subdomain Discovery — Passive Enum
**ID:** `subdomain_discovery` · **Safety:** Safe · **Dependency:** `subfinder`
Passive subdomain enumeration via multiple external sources.

### 3. 🛰️ Scapy Recon — Low-level Probing
**ID:** `scapy_recon` · **Safety:** Safe · **Dependency:** `scapy`
Custom packet crafting for ARP/ICMP discovery.

### 4. 🕵️ WHOIS Lookup — Domain Intelligence
**ID:** `whois_lookup` · **Safety:** Safe · **Dependency:** `whois`
Registration details and contact information retrieval.

### 5. 📦 DNS Enumeration — Record Discovery
**ID:** `dns_enum` · **Safety:** Safe · **Dependency:** `dnsrecon`
Detailed DNS record analysis and zone transfer testing.

---

## 🌐 Web Reconnaissance

### 6. 🌍 HTTP Inspector — Endpoint Analysis
**ID:** `http_inspector` · **Safety:** Safe · **Dependency:** `curl`
Headers, status codes, and basic endpoint verification.

### 7. 🔐 TLS Inspector — Cipher Audit
**ID:** `tls_inspector` · **Safety:** Safe · **Dependency:** `openssl`
SSL/TLS certificate validation and protocol analysis.

### 8. 📂 Directory Discovery — Path Fuzzing
**ID:** `dir_discovery` · **Safety:** Intrusive · **Dependency:** `ffuf`
Brute-force discovery of hidden files and directories.

### 9. 🔎 Nikto — Web Vulnerability Scanner
**ID:** `nikto` · **Safety:** Intrusive · **Dependency:** `nikto`
Comprehensive web server security scanning.

### 10. 🧬 Nuclei — Template-based Scanner
**ID:** `nuclei` · **Safety:** Intrusive · **Dependency:** `nuclei`
Fast, template-driven vulnerability detection.

### 11. 🧪 SQLi Checker — Feasibility Test
**ID:** `sqli_checker` · **Safety:** Intrusive · **Dependency:** `ghauri`
Lightweight investigation of potential SQL injection vectors.

---

## 📝 CMS Security

### 12. 📝 WPScan — WordPress Auditor
**ID:** `wpscan` · **Safety:** Intrusive · **Dependency:** `wpscan`
Specialized WordPress vulnerability and plugin scanner.

### 13. 🏷️ JoomScan — Joomla Scanner
**ID:** `joomscan` · **Safety:** Intrusive · **Dependency:** `joomscan`
Vulnerability and configuration auditor for Joomla CMS.

### 14. 🛡️ DroopeScan — Drupal/Silverstripe Audit
**ID:** `droopescan` · **Safety:** Intrusive · **Dependency:** `droopescan`
Plugin and theme discovery for Drupal and Silverstripe.

---

## 🔐 Exploit & Expert Mode

### 15. 💉 SQLMap — SQL Injection Automated
**ID:** `sqlmap` · **Safety:** Exploit · **Dependency:** `sqlmap`
Full-featured SQL injection exploitation and database takeover.

### 16. 🚀 Metasploit — Exploit Connector
**ID:** `metasploit` · **Safety:** Intrusive · **Dependency:** `msfconsole`
Integration with the Metasploit framework for advanced exploitation.

### 17. ⚡ Hashcat — Password Recovery
**ID:** `hashcat` · **Safety:** Intrusive · **Dependency:** `hashcat`
High-speed GPU-capable (emulated) password cracking.

---

## 🔬 Forensics & Analysis

### 18. 🔬 YARA — Pattern Matching
**ID:** `yara_scan` · **Safety:** Intrusive · **Dependency:** `yara`
Forensic logic and malware pattern matching.

### 19. 🧠 Volatility — Memory Forensics
**ID:** `volatility` · **Safety:** Intrusive · **Dependency:** `volatility3`
Advanced memory image analysis and artifact extraction.

---

## 💻 System & Code Security

### 20. 🔑 Secret Scanner — Leak Detection
**ID:** `secret_scanner` · **Safety:** Safe · **Dependency:** `gitleaks`
Detection of hardcoded secrets in source code and history.

### 21. 🛡️ Bandit — Static Code Analysis
**ID:** `code_analyzer` · **Safety:** Safe · **Dependency:** `bandit`
Security-focused static analysis for Python projects.

### 22. 💻 SSH Runner — Auth & Config Audit
**ID:** `ssh_runner` · **Safety:** Intrusive · **Dependency:** `ssh`
Verification of SSH configurations and authorized access.

---

## Safety Metrics

| Tier | Count | Description |
|------|-------|-------------|
| **Safe** | 9 | Passive observation, low impact |
| **Intrusive**| 12 | Active probing, high traffic |
| **Exploit** | 1 | Potential state modification |
| **Total** | **22** | |

---

**Last Updated:** 2026-03-25  
**Version:** 1.3.0 (Phase 3 Verified)
