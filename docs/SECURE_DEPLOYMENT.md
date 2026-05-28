# SecuScan Secure Deployment Guide

## Overview

This document describes the operational threat model, deployment assumptions, trust boundaries, and recommended hardening guidance for SecuScan deployments.

SecuScan is designed as a local-first security platform intended for educational, research, and authorized security testing workflows.

---

# Threat Model

## Sensitive Assets

The following assets should be treated as security-sensitive:

* API credentials
* Authentication tokens
* Environment secrets
* Plugin execution environment
* Scan results and exported reports
* Database contents
* Deployment configuration
* Vault or secret-management credentials

---

## Threat Actors

| Threat Actor              | Example Risks              |
| ------------------------- | -------------------------- |
| Anonymous remote attacker | Unauthorized API access    |
| Malicious plugin author   | Arbitrary code execution   |
| Internal network attacker | Credential theft           |
| Compromised container     | Host compromise            |
| Misconfigured operator    | Accidental public exposure |

---

## Trust Boundaries

| Boundary                   | Trust Level                 | Risks                     |
| -------------------------- | --------------------------- | ------------------------- |
| Browser ↔ API Server       | Untrusted                   | Token theft, MITM attacks |
| Plugin ↔ Core Application  | Partially trusted           | Arbitrary code execution  |
| Container ↔ Host System    | Untrusted                   | Privilege escalation      |
| Application ↔ Secret Store | Trusted with authentication | Secret leakage            |

---

# Local-First Security Assumptions

SecuScan is designed primarily for localhost and trusted-user workflows.

The default development setup assumes:

* The operator controls the local machine
* Services bind to `127.0.0.1`
* Docker sandboxing is available where required
* Plugins are manually installed by the operator
* Scan targets are authorized systems

Deployments that expose SecuScan outside localhost require additional hardening and authentication controls.

---

# Authentication Requirements

## Recommendations

* Require authentication for all non-local deployments
* Disable anonymous administrative access
* Use strong randomly generated secrets
* Rotate credentials regularly
* Avoid shared operator accounts
* Restrict privileged administrative access

---

# Secret & Vault Management

## Recommended Practices

* Store secrets in environment variables or external secret managers
* Never commit secrets to git repositories
* Rotate credentials regularly
* Restrict access permissions to secret stores
* Separate development and production credentials

## Avoid

* Hardcoding secrets in source code
* Logging sensitive credentials
* Sharing `.env` files
* Reusing production credentials locally

---

# Plugin Security Risks

Plugins should be treated as potentially untrusted code.

## Risks

* Arbitrary file access
* Data exfiltration
* Credential theft
* Remote code execution
* Unsafe subprocess execution

## Recommendations

* Install only trusted plugins
* Review plugin source code before deployment
* Disable unused plugins
* Restrict plugin filesystem access where possible
* Avoid dynamic plugin loading in production deployments

---

# Network Exposure

## Recommended Architecture

Internet
↓
Reverse Proxy (TLS)
↓
SecuScan Application
↓
Internal Database / Services

---

## Recommendations

* Do not expose internal admin endpoints publicly
* Restrict access using firewalls or VPNs
* Enable HTTPS/TLS when exposed on LAN or public networks
* Bind local deployments to localhost where possible
* Disable debug configurations in production

---

# Deployment Profiles

## Local Development

### Intended Use

Single-user development environment.

### Recommendations

* Bind services to `127.0.0.1`
* Use development-only credentials
* Avoid exposing ports publicly
* Disable unnecessary plugins

### Risks

* Local malware
* Browser extension token theft

---

## LAN Deployment

### Intended Use

Trusted internal/private network deployments.

### Recommendations

* Enable authentication
* Restrict firewall access
* Use TLS internally where possible
* Limit admin access to trusted devices

### Risks

* Lateral movement attacks
* Weak internal passwords

---

## Container Deployment

### Recommendations

* Run containers as non-root users
* Use read-only filesystems where possible
* Drop unnecessary Linux capabilities
* Use minimal base images
* Mount secrets securely
* Restrict outbound network access

Example Kubernetes security context:

```yaml
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
```

---

# Hardening Checklist

## Authentication

* [ ] Authentication enabled
* [ ] Default credentials removed
* [ ] Administrative access restricted

## Secrets

* [ ] Secrets stored outside repository
* [ ] Secret rotation policy established
* [ ] `.env` files excluded from version control

## Containers

* [ ] Running as non-root
* [ ] Minimal container image used
* [ ] Unnecessary Linux capabilities removed

## Network

* [ ] TLS enabled
* [ ] Firewall configured
* [ ] Public exposure minimized

## Monitoring

* [ ] Audit logging enabled
* [ ] Error logs monitored
* [ ] Alerts configured where applicable

---

# Operator Responsibilities

Operators are responsible for:

* Securing deployment infrastructure
* Managing credentials securely
* Reviewing plugins before installation
* Applying security updates regularly
* Restricting unnecessary network exposure
