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

> The concrete variables (`SECUSCAN_VAULT_KEY`, `SECUSCAN_ADMIN_API_KEY`,
> `SECUSCAN_PLUGIN_SIGNATURE_KEY`) and their defaults are listed in the
> [Environment Variable Matrix](#environment-variable-matrix).

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

# Webhook Security Constraints

SecuScan deployments may integrate with outbound webhooks for notifications, automation workflows, or external integrations. Operators should treat webhook destinations as untrusted network targets unless explicitly approved.

## SSRF Risk

Webhook functionality can introduce Server-Side Request Forgery (SSRF) risks if arbitrary destinations are allowed.

Potential impacts include:

* Access to internal-only services
* Access to cloud metadata endpoints
* Network reconnaissance of private infrastructure
* Data exfiltration through attacker-controlled endpoints

## Recommended Restrictions

Operators should:

* Maintain an allowlist of approved webhook destinations
* Restrict webhook traffic to trusted HTTPS endpoints
* Block requests to localhost (`127.0.0.1`, `::1`)
* Block requests to private RFC1918 address ranges where possible
* Block access to cloud metadata services
* Avoid forwarding sensitive credentials in webhook payloads

## Safe Operator Configuration

When enabling webhook integrations:

* Review all configured destinations before deployment
* Use dedicated webhook credentials where supported
* Enable outbound firewall filtering when possible
* Monitor webhook delivery failures and unexpected destinations
* Remove unused webhook configurations regularly

Webhook integrations should be treated as external trust boundaries and reviewed during security audits.

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

### Docker Sandbox Network Isolation

When running in Docker-sandboxed mode (`SECUSCAN_DOCKER_ENABLED=true`), SecuScan executes standard plugins inside isolated container sandboxes.

To ensure strict network isolation and prevent lateral movement or inter-container communication (ICC):
* SecuScan uses a dedicated Docker bridge network defined by the environment variable `SECUSCAN_DOCKER_NETWORK` (defaults to `restricted`).
* If this network does not exist, the Task Executor will **automatically create it** on first use with `--opt com.docker.network.bridge.enable_icc=false` (Inter-Container Communication disabled). This ensures sandbox containers cannot talk to each other or the host's private endpoints.
* If ICC-disabled network creation fails, it will attempt a standard bridge fallback before failing with a fatal runtime error.

See the [Environment Variable Matrix](#environment-variable-matrix) for the full set of
sandbox/Docker variables (`SECUSCAN_DOCKER_ENABLED`, `SECUSCAN_SANDBOX_ALLOW_NETWORK`,
resource caps) and their defaults.

---

# Environment Variable Matrix

The tables below summarize the **security-significant** environment variables, their
defaults, and operational impact, so operators can review the active security posture in
one place rather than tracing it across modules.

**How configuration works:**

* All backend settings use the **`SECUSCAN_`** prefix and are case-insensitive
  (e.g. `safe_mode_default` → `SECUSCAN_SAFE_MODE_DEFAULT`).
* The single source of truth is `Settings` in
  [`backend/secuscan/config.py`](../backend/secuscan/config.py);
  [`.env.example`](../.env.example) is a copy-ready starter. Not every variable below is
  pre-listed in `.env.example` — unset variables fall back to the defaults shown here.
* List-valued variables accept either a comma-separated string or a JSON array.
* Defaults shown are the secure-by-default **development** values. Production deployments
  should harden the values flagged below.

> Only a curated, security-relevant subset is documented here. Purely functional/integration
> settings (database path, Redis URL, cache TTLs, data directories, SMTP, AI summary, DNS
> timeouts, workflow interval, per-bucket rate-limit windows) live in `config.py` and, where
> common, `.env.example`.

## Server & Exposure

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_BIND_ADDRESS` | `127.0.0.1` | Interface the API binds to. Keep loopback for local-first use; binding `0.0.0.0` exposes the API to the network — put TLS + authentication in front first. |
| `SECUSCAN_BIND_PORT` | `8000` | API listen port. |
| `SECUSCAN_DEBUG` | `true` | Debug mode. **Set `false` in production** — debug output can leak internal details. |
| `SECUSCAN_CORS_ALLOWED_ORIGINS` | localhost dev origins | Browser origins allowed to call the API. Tighten to your real frontend origin in production; avoid wildcards. |
| `SECUSCAN_CORS_ALLOWED_HEADERS` | `Content-Type,Authorization,X-Api-Key,Accept,Origin` | Browser request headers allowed during CORS preflight. Keep `X-Api-Key` when overriding this value so the web UI can establish an authenticated session. |

## Secrets & Authentication

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_VAULT_KEY` | _unset_ — **required** | Master key for the encrypted credential vault. The server refuses to start the vault if unset. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. Never commit. |
| `SECUSCAN_ADMIN_API_KEY` | _unset_ | Token gating admin endpoints (e.g. network-policy administration). Set a strong random value for any non-local deployment. |
| `SECUSCAN_PLUGIN_SIGNATURE_KEY` | _unset_ | Signing key for plugin signature verification (also used as a vault-key fallback). Set when enforcing signatures. |
| `SECUSCAN_ENFORCE_PLUGIN_SIGNATURES` | `false` | When `true`, plugins must carry a valid signature to load. Enable in production or untrusted-plugin environments. |

## Execution Safety Guards

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_SAFE_MODE_DEFAULT` | `true` | Default safe-mode for tasks; blocks intrusive/exploit behavior unless explicitly overridden. Keep `true`. |
| `SECUSCAN_REQUIRE_CONSENT` | `true` | Requires explicit consent before a scan runs. Keep `true` — a core authorized-use guard. |
| `SECUSCAN_DENIED_CAPABILITIES` | _empty_ | Comma-separated capabilities denied across all plugins (`network, filesystem, docker, credentials, intrusive, exploit`). e.g. `exploit,credentials` hard-disables those plugins before execution. |
| `SECUSCAN_ALLOW_LOOPBACK_SCANS` | `true` | Whether scans may target loopback addresses. Consider `false` in shared/multi-user deployments. |

## Network Egress Policy

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_ENFORCE_NETWORK_POLICY` | `true` | Master switch for egress allow/deny enforcement. Keep `true`. |
| `SECUSCAN_NETWORK_POLICY_FAILURE_MODE` | `block` | `block` (deny on policy error) or `log_only`. Keep `block` in production. |
| `SECUSCAN_NETWORK_ALLOWLIST` | _empty_ | CIDRs permitted for egress. Set explicitly to authorize targets. |
| `SECUSCAN_NETWORK_DENYLIST` | metadata + RFC1918 + IPv6 ULA/link-local/loopback | CIDRs blocked from egress: `169.254.169.254/32`, `169.254.0.0/16`, `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `100.64.0.0/10`, `fc00::/7`, `fe80::/10`, `::1/128`. Prevents SSRF to internal/cloud-metadata services — **do not weaken**. |
| `SECUSCAN_ALLOWED_NETWORKS` | `127.0.0.1,192.168.*.*,10.*.*.*,172.16.*.*` | Glob allowlist for scan **targets** (distinct from the CIDR egress policy above). |

## Notification / Webhook SSRF

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_NOTIFICATION_SSRF_ENABLED` | `true` | SSRF protection on outbound notification/webhook calls. Keep `true`. |
| `SECUSCAN_NOTIFICATION_BLOCKED_IP_RANGES` | metadata + private + multicast | IP ranges webhooks cannot reach; blocks metadata/internal exfiltration. |
| `SECUSCAN_NOTIFICATION_ALLOWED_PORTS` | `80,443,8080,8443` | Ports webhook destinations may use. |
| `SECUSCAN_NOTIFICATION_MAX_REDIRECTS` | `0` | Redirects followed on webhook delivery. `0` prevents redirect-based SSRF bypass. |

## Sandbox / Docker Isolation

See [Docker Sandbox Network Isolation](#docker-sandbox-network-isolation) above for the
network behavior of these variables.

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_DOCKER_ENABLED` | `false` | Run plugins inside Docker sandboxes. Enable for stronger isolation of untrusted plugins. |
| `SECUSCAN_DOCKER_NETWORK` | `restricted` | Bridge network for sandbox containers; auto-created with inter-container communication disabled. |
| `SECUSCAN_SANDBOX_ALLOW_NETWORK` | `true` | Whether sandboxed plugins get network access. Set `false` to fully isolate. |
| `SECUSCAN_SANDBOX_TIMEOUT` | `600` | Max seconds a sandboxed task may run; caps runaway execution. |
| `SECUSCAN_SANDBOX_MEMORY_MB` / `SECUSCAN_SANDBOX_CPU_QUOTA` | `512` / `0.5` | Memory (MB) and CPU-quota caps on sandbox containers (resource-exhaustion containment). |
| `SECUSCAN_PARSER_SANDBOX_TIMEOUT_SECONDS` | `30` | Timeout for the isolated `parser.py` subprocess. |
| `SECUSCAN_PARSER_SANDBOX_MAX_OUTPUT_BYTES` | `8388608` (8 MB) | Output cap for the parser subprocess (memory-exhaustion guard). |

## Rate Limiting & Abuse Control

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_MAX_CONCURRENT_TASKS` | `3` | Concurrent scan ceiling. |
| `SECUSCAN_MAX_TASKS_PER_HOUR` | `50` | Hourly scan quota. |
| `SECUSCAN_MAX_REQUESTS_PER_MINUTE` | `100` | Global API request-rate cap. |
| `SECUSCAN_TRUSTED_PROXIES` | `127.0.0.1,::1` | Proxies trusted for client-IP resolution (rate-limit accuracy). Only list proxies you control. |
| `SECUSCAN_TASK_START_MAX_BODY_BYTES` | `64000` | Max task-start JSON body in bytes (request-flood guard). |

## Logging & Audit

| Variable | Default | Operational / security impact |
| -------- | ------- | ----------------------------- |
| `SECUSCAN_LOG_LEVEL` | `INFO` | Log verbosity. Avoid `DEBUG` in production — it may log sensitive detail. |
| `SECUSCAN_NETWORK_AUDIT_LOG_FILE` | `logs/network.audit.log` | Path to the egress-decision audit log. |
| `SECUSCAN_NETWORK_AUDIT_RETENTION_DAYS` | `90` | Retention window for the network audit log. |

> ⚠️ Authorized use only. These variables tune guardrails — they do not remove the
> operator's responsibility to scan only systems they own or are explicitly permitted to
> assess.

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
