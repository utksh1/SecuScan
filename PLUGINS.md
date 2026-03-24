# SecuScan MVP Plugins - Complete ✅

## All 5 MVP Plugins Implemented

### 1. 🌐 HTTP Inspector
**Status:** ✅ Complete  
**File:** `plugins/http_inspector/metadata.json`

- **Purpose:** Inspect HTTP/HTTPS endpoints for headers, cookies, and TLS configuration
- **Safety Level:** Safe (read-only)
- **Presets:** 2 (quick, full)
- **Fields:** 3 (url, follow_redirects, timeout)
- **Rate Limit:** 100/hour, max 5 concurrent
- **Dependencies:** curl

**Use Cases:**
- Validate URL availability
- Examine response headers
- Check security headers (HSTS, CSP, etc.)
- Inspect TLS configuration

---

### 2. 🔍 Nmap
**Status:** ✅ Complete  
**File:** `plugins/nmap/metadata.json`

- **Purpose:** Network discovery and port scanning
- **Safety Level:** Safe (with aggressive scan warnings)
- **Presets:** 5 (quick, top100, top1000, service_fingerprint, comprehensive)
- **Fields:** 8 (target, preset, ports, scan_type, service_detection, os_detection, timeout, safe_mode)
- **Rate Limit:** 10/hour, max 2 concurrent
- **Dependencies:** nmap

**Presets:**
- **Quick:** Top 100 ports, fast scan
- **Top 100:** Common services, safe mode
- **Top 1000:** Extended coverage with service detection
- **Service Fingerprint:** Version detection, no safe mode
- **Comprehensive:** Full port range + OS detection (Advanced)

**Scan Types:**
- SYN Scan (stealth)
- Connect Scan
- UDP Scan

---

### 3. 🔐 TLS Inspector
**Status:** ✅ Complete  
**File:** `plugins/tls_inspector/metadata.json`

- **Purpose:** Examine TLS/SSL certificates and cipher configurations
- **Safety Level:** Safe (passive observation)
- **Presets:** 3 (quick, full, custom_port)
- **Fields:** 7 (host, port, hostname, show_chain, check_ciphers, check_protocols, timeout)
- **Rate Limit:** 50/hour, max 3 concurrent
- **Dependencies:** openssl

**Features:**
- Certificate validity checking
- Certificate chain analysis
- Cipher suite enumeration
- Protocol version testing (SSLv2, SSLv3, TLS 1.0-1.3)
- Expiry date warnings

---

### 4. 📂 Directory Discovery
**Status:** ✅ Complete  
**File:** `plugins/dir_discovery/metadata.json`

- **Purpose:** Discover hidden directories and files on web servers
- **Safety Level:** Intrusive (generates significant traffic)
- **Presets:** 3 (quick, standard, deep)
- **Fields:** 9 (base_url, wordlist, extensions, threads, delay_ms, match_codes, recursive, max_depth, timeout)
- **Rate Limit:** 5/hour, max 1 concurrent
- **Dependencies:** ffuf (or similar)

**Wordlists:**
- **Small:** 108 entries (included) - 1-2 min
- **Medium:** ~5,000 entries (external) - 5-10 min
- **Large:** ~50,000 entries (external) - 30+ min

**Presets:**
- **Quick:** Small wordlist, polite (100ms delay)
- **Standard:** Medium wordlist, balanced (50ms delay)
- **Deep:** Large wordlist + extensions + recursive (10ms delay)

**Safety Features:**
- Rate limiting between requests
- Configurable thread count
- Delay controls to prevent server overload

---

### 5. 🔎 Nikto
**Status:** ✅ Complete  
**File:** `plugins/nikto/metadata.json`

- **Purpose:** Web server vulnerability scanner
- **Safety Level:** Intrusive (can trigger alerts)
- **Presets:** 3 (passive, standard, active)
- **Fields:** 7 (target, preset, check_categories, timeout, safe_mode, ssl_check, follow_redirects)
- **Rate Limit:** 3/hour, max 1 concurrent
- **Dependencies:** nikto, perl

**Check Categories:**
- Security Headers
- SSL/TLS Configuration
- HTTP Methods
- Sensitive Paths
- Software Versions
- Injection Tests (active mode only)

**Scan Modes:**
- **Passive:** Headers, SSL, versions only
- **Standard:** + Methods and paths checks
- **Active:** + Injection and exploit tests ⚠️

**Warning:** Active mode may trigger IDS/IPS alerts and attempt exploit checks.

---

## Plugin Statistics

| Metric | Count |
|--------|-------|
| **Total Plugins** | 5 |
| **Safe Level** | 3 (HTTP, TLS, Nmap) |
| **Intrusive Level** | 2 (Directory, Nikto) |
| **Total Presets** | 16 |
| **Total Fields** | 34 |
| **Dependencies** | curl, nmap, openssl, ffuf, nikto |

## Safety Classification

### Safe Plugins (3)
- HTTP Inspector: Read-only requests
- TLS Inspector: Passive certificate inspection
- Nmap: Port scanning (with rate limits)

### Intrusive Plugins (2)
- Directory Discovery: High traffic generation
- Nikto: Active vulnerability probing

## Usage Examples

### HTTP Inspector - Quick Check
```json
{
  "plugin_id": "http_inspector",
  "preset": "quick",
  "inputs": {
    "url": "https://example.com"
  },
  "consent_granted": true
}
```

### Nmap - Service Detection
```json
{
  "plugin_id": "nmap",
  "preset": "service_fingerprint",
  "inputs": {
    "target": "192.168.1.1"
  },
  "consent_granted": true
}
```

### TLS Inspector - Certificate Check
```json
{
  "plugin_id": "tls_inspector",
  "preset": "full",
  "inputs": {
    "host": "example.com",
    "port": 443
  },
  "consent_granted": true
}
```

### Directory Discovery - Quick Scan
```json
{
  "plugin_id": "dir_discovery",
  "preset": "quick",
  "inputs": {
    "base_url": "https://example.com"
  },
  "consent_granted": true
}
```

### Nikto - Passive Assessment
```json
{
  "plugin_id": "nikto",
  "preset": "passive",
  "inputs": {
    "target": "https://example.com"
  },
  "consent_granted": true
}
```

---

## Installation Requirements

Before using these plugins, ensure dependencies are installed:

```bash
# macOS
brew install nmap openssl curl perl
brew install ffuf  # or use dirb/gobuster
brew install nikto

# Ubuntu/Debian
sudo apt-get install nmap openssl curl perl
sudo apt-get install ffuf
sudo apt-get install nikto

# Verify installations
nmap --version
openssl version
curl --version
ffuf --version
nikto -Version
```

---

## Wordlists Setup

The Directory Discovery plugin requires wordlists:

### Included
- ✅ `wordlists/small.txt` (108 entries)

### Optional (for medium/large scans)
```bash
cd wordlists
git clone https://github.com/danielmiessler/SecLists.git
ln -s SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt medium.txt
ln -s SecLists/Discovery/Web-Content/directory-list-2.3-big.txt large.txt
```

---

## Next Steps

All MVP plugins are complete! Next priorities:

1. ✅ **Test each plugin** with the backend API
2. 📱 **Build Frontend SPA** to provide GUI access
3. 🧪 **Write Tests** for plugin loading and execution
4. 📚 **Add Parser Modules** for structured output formatting
5. 🐳 **Implement Docker Sandboxing** for isolation

---

**Last Updated:** 2025-10-29  
**Status:** All 5 MVP Plugins Complete ✅
