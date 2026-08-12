# Curated 100 distinct GitHub issues for SecuScan.
# Each: title, body, type, area, priority
# type:  type:bug | type:feature | type:security | type:refactor | type:performance
# area:  area:backend | area:frontend | area:plugins
# priority: priority:high | priority:medium | priority:low

ISSUES = [
# ---------------- BACKEND BUGS / SECURITY (1-30) ----------------
{
 "title": "Disable TLS certificate verification in crawler allows MITM/SSRF",
 "body": "crawler.py:89 opens an httpx client with verify=False and follow_redirects=True. Scanners follow redirects to any host with no certificate validation, enabling MITM and redirect-based SSRF to internal HTTPS endpoints.\n\nFix: use verify=True (or a configurable SECUSCAN_TLS_VERIFY), and do not follow redirects to hosts other than the original target.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Network policy default-allow exposes all public egress (incl. cloud metadata IP)",
 "body": "network_policy.py:444-452: when SECUSCAN_NETWORK_ALLOWLIST is empty, the engine adds allow rules for 0.0.0.0/0 and ::/0. The default denylist does not contain 169.254.169.254 (cloud metadata) unless the operator adds it, so SSRF to http://169.254.169.254/ is permitted by the policy layer. IPv6 is unconstrained by a typical IPv4-only denylist.\n\nFix: ship a default denylist with link-local/metadata ranges and require an explicit allowlist for non-internal targets.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "network_policy.check_access has no DNS-rebinding protection",
 "body": "network_policy.py:216-221 resolves the target with socket.gethostbyname (IPv4 only, blocking, no timeout) and allows based on that single resolution. An attacker-controlled domain can resolve to a public IP at check time and an internal IP at connect time. validate_target does a rebind check but the network layer does not.\n\nFix: resolve once, pin the IP, and enforce the same IP at connect time (or route egress through a validating proxy).",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Plugins with missing/malformed metadata.json are silently dropped at load",
 "body": "plugins.py:141-142 swallows every exception (bad JSON, Pydantic failure, missing fields) with only logger.error. Several plugin dirs ship with no metadata.json at all and vanish with no hard failure; operators cannot tell a plugin was dropped.\n\nFix: treat missing/corrupt metadata as a loud error (or add a --strict load mode) and surface a load report.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:high",
},
{
 "title": "plugin_validator.py is not wired into runtime plugin loading",
 "body": "plugins.py:_validate_plugin is a bespoke weaker validator that does not call PluginMetadataValidator. The richer checks (category enum, field-type enum, parser-type enum, duplicate ids, checksum length) only run via scripts/validate_plugins.py. So bad metadata is never caught at load.\n\nFix: invoke PluginMetadataValidator from PluginManager._validate_plugin and gate loading on result.valid.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:high",
},
{
 "title": "Schema mismatch: validator accepts field types the model rejects",
 "body": "plugin_validator.py:VALID_FIELD_TYPES includes 'number'/'textarea' but models.py PluginFieldType has neither. A plugin declaring type:'number' passes the CLI validator but fails PluginMetadata Pydantic parsing at runtime -> silently dropped.\n\nFix: derive VALID_FIELD_TYPES from PluginFieldType so they cannot diverge.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "Explicit capabilities can downgrade enforcement (safety escape hatch)",
 "body": "capabilities.py:116-121 effective_capabilities treats a non-empty declared list as the sole source of truth and ignores the safety-level implied set. A plugin with safety.level 'exploit' could declare capabilities:['network'] to evade SECUSCAN_DENIED_CAPABILITIES=exploit.\n\nFix: union the declared set with the implied set.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "CLI and workflow scheduler bypass plugin consent",
 "body": "cli.py:54 and workflows.py:187 pass consent_granted=True unconditionally. For intrusive/exploit plugins that declare requires_consent, consent is forcibly granted without presenting consent_message.\n\nFix: require explicit user consent (or a stored approval record) before executing requires_consent plugins.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Workflow concurrency limit is not actually enforced",
 "body": "workflows.py:192-202 calls concurrent_limiter.acquire(task_id); if it returns False the task is marked failed but asyncio.create_task(run_task(task_id)) is still scheduled unconditionally at line 202, so the 'failed' task still executes.\n\nFix: only schedule run_task when the acquire succeeds.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Signature declared but unverified is accepted at exec time",
 "body": "plugins.py:241: when plugin.signature is set but plugin_signature_key is missing and enforcement is OFF, it logs a warning and returns True. A plugin carrying a signature but no key configured is executed without verification.\n\nFix: if a signature is present, require the key regardless of enforcement flag.",
 "type": "type:security", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "Redis scan rate limiter trusts X-Forwarded-For without trusted-proxy check",
 "body": "rate_limiter.py:62-66 takes the first X-Forwarded-For value unconditionally. An attacker can spoof it to make the limiter track a victim IP (and get themselves blocked) or rotate the header to bypass limits. ratelimit.resolve_client_identity checks settings.trusted_proxies, but this limiter does not.\n\nFix: only honor X-Forwarded-For when request.client.host is a trusted proxy.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Raw API keys embedded in rate-limit identity leak into logs",
 "body": "ratelimit.py:124,130 builds client identity as 'apikey:{value}' embedding the literal secret. This string is used as a dict key and can appear in debug logs or exception traces, leaking the API key.\n\nFix: hash the key (e.g. apikey:{sha256(value)[:16]}) instead of embedding it.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Redis INCR/EXPIRE race can permanently block an IP",
 "body": "rate_limiter.py: INCR then EXPIRE are not atomic; if EXPIRE is lost (Redis reconnect) the counter key persists forever with no TTL, permanently blocking the IP (DoS).\n\nFix: use INCR with EXPIRE only when TTL is -1, or a single SET ... NX EX command.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Scan rate limiter fails open on Redis errors (limits silently disabled)",
 "body": "rate_limiter.py:165-169 any Redis exception allows the request. If Redis is down, rate limiting is silently disabled for scan endpoints - an abuse vector during outages.\n\nFix: make fail-open/fail-closed configurable and log a security warning when limiting is disabled.",
 "type": "type:security", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "saved_views API has no ownership/tenant check (IDOR)",
 "body": "saved_views.py create/list/update/delete perform no authorization or owner scoping. Any caller can list all users' views or overwrite/delete another user's saved view by view_id. In multi-tenant deployments this is an IDOR.\n\nFix: scope all saved_view operations by owner_id and reject cross-tenant access.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "redact() misses JWTs, DB connection URIs, and userinfo URLs",
 "body": "redaction.py:32-153 has no pattern for eyJ... JWTs, mongodb:// / postgres:// / mysql:// / redis:// / amqp:// URIs with embedded credentials, and user:pass@host in URLs. These leak into reports/logs.\n\nFix: add patterns for JWTs and common connection-string schemes.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "target field is never redacted in reports/emails/Slack",
 "body": "reporting.py:_normalize_finding applies redact() to description/proof/confidence_reason but never to target; notification_service.py embeds finding.get('target') in subjects/Slack payloads without redact(). Internal hostnames/IPs/credentials embedded in target leak in every format.\n\nFix: apply redact() to target and walk evidence values with recursive redaction.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Webhook response buffered unbounded into memory (DoS)",
 "body": "notification_service.py:173-181 concatenates all response chunks with no size limit. A hostile/compromised webhook can send GBs and exhaust memory.\n\nFix: cap bytes (e.g. break after MAX) and pass max_redirects to httpx.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Slack/email alerts include raw error_message without redaction",
 "body": "notification_service.py embeds task.get('error_message') and target into Slack webhooks with no redact(). Scanner error messages often contain commands, IPs, or internal paths.\n\nFix: redact() all dynamic values before building external alert payloads.",
 "type": "type:security", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "DNS resolution in send_webhook blocks the event loop",
 "body": "notification_service.py:331 uses synchronous socket.getaddrinfo inside an async function without asyncio.to_thread, stalling the event loop on slow/malicious DNS.\n\nFix: wrap resolution in asyncio.to_thread or use an async resolver.",
 "type": "type:performance", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Future-dated findings scored oldest but described as recent",
 "body": "risk_scoring.py:61-70 returns 1.0 (lowest) for future discovered_at, but _recency_detail line 216 labels future dates 'very recent' (high). A future-dated finding is described as recent yet scored oldest - contradictory.\n\nFix: make the score and the detail consistent for future dates.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Info-severity findings default to 5.0/10 risk score",
 "body": "risk_scoring.py:54,76: with no exploitable/exposure/date/confidence data, compute_risk_score returns 5*0.30+5*0.25+5*0.20+5*0.15+5*0.10 = 5.0. 'Info' findings get a non-trivial 5.0 by default, skewing prioritization. Defaults should be lower (e.g. 0) when unknown.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "CacheClient has no locking; eviction/sweep can leave inconsistent TTL state",
 "body": "cache.py:50-87 mutates three dicts without a lock; get_json can resurrect a key whose _expires entry was swept, returning a value with no TTL check. Capacity checks before insertion allow growth past max_entries under concurrency.\n\nFix: use asyncio.Lock and keep the three dicts in sync, or use a single TTLMap.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Vault blob has no key-version/id marker for rotation",
 "body": "vault.py: the wire format is nonce||ciphertext with no key-id/version header. On key rotation, old blobs can't be distinguished from new ones and a wrong-key decrypt only fails at GCM auth (no way to know which key to try).\n\nFix: prepend a key-version/id header to the stored blob.",
 "type": "type:refactor", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "_resolve_wordlist_path falls through to raw, unvalidated value",
 "body": "plugins.py:513-519: if the wordlist value matches no alias and no candidate exists, the function returns the original value without confirming it exists or stays within the wordlists dir, so the scanner receives a possibly-nonexistent arbitrary relative path.\n\nFix: raise an error instead of returning the raw value.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "Unknown input fields bypass validation via __ prefix",
 "body": "plugins.py:563 _validate_inputs_against_schema skips any field starting with __, so a caller can submit __target/__evil to bypass 'unknown field' rejection (they're ignored, but it weakens schema enforcement and can mask typos).\n\nFix: only skip known internal control fields explicitly, not a whole prefix.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "CapabilityEnforcer crashes app startup on bad denied token",
 "body": "capabilities.py:144-150 raises ValueError from build_enforcer_from_settings on an unrecognized token in SECUSCAN_DENIED_CAPABILITIES, which can abort startup. The code itself notes a misconfigured denylist 'silently fails to enforce'.\n\nFix: warn-and-ignore unknown tokens instead of raising.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "plugin_validator skips placeholder validation inside --if tokens",
 "body": "plugin_validator.py:190-191 _check_command_template continues on any --if: token, so placeholders inside then/else segments (e.g. --if:scan_type:then:-s{scan_type}) are never checked against declared field ids. A typo like {scan_tpye} passes validation but yields an empty value at runtime.\n\nFix: also scan --if then/else segments for placeholders.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "Top-level validation block validated but never used",
 "body": "plugin_validator.py _check_validation_block validates a top-level 'validation' key, but PluginMetadata has no such field and all real validation lives in per-field field.validation. Dead/confusing feature giving a false sense of enforcement.\n\nFix: remove it or wire it to actual field validation.",
 "type": "type:refactor", "area": "area:plugins", "priority": "priority:low",
},

# ---------------- PLUGINS / SANDBOX (31-50) ----------------
{
 "title": "amass writes to a hardcoded predictable /tmp/amass path",
 "body": "plugins/amass/metadata.json command_template uses '-dir','/tmp/amass'. World-writable predictable path = symlink/hijack and cross-user collision; never cleaned.\n\nFix: use tempfile.mkdtemp() resolved at runtime and pass via an injected field, or a per-task sandbox dir.",
 "type": "type:security", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "parser_sandbox retains PYTHONPATH/HOME (sandbox escape vector)",
 "body": "parser_sandbox.py:109 _sanitised_env keeps PATH, PYTHONPATH, HOME, TMPDIR, etc. An inherited PYTHONPATH pointing at an attacker-controlled directory lets the 'sandboxed' parser import arbitrary modules. No privilege drop.\n\nFix: drop PYTHONPATH (or reset to a fixed safe value) and run the parser child as an unprivileged user.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "Parser subprocess children/grandchildren not killed on timeout",
 "body": "parser_sandbox.py:204-208 on timeout calls proc.kill() on the direct child only; any subprocess the parser spawns survives.\n\nFix: put the child in its own process group (start_new_session=True) and os.killpg.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "sandbox_executor memory-limit unit bug across platforms",
 "body": "sandbox_executor.py:204-207: Linux ru_maxrss is KB (x1024 -> bytes) but macOS reports bytes; the code multiplies by 1024 on both, so on macOS rss_bytes is 1024x too large, making memory-limit detection wrong.\n\nFix: branch on platform.system() for the unit.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "SandboxConfig.allow_network is never enforced (dead field)",
 "body": "models.py SandboxConfig.allow_network defaults True but sandbox_executor.py never applies any network restriction (no netns/seccomp/iptables). The field is dead.\n\nFix: implement it or remove it.",
 "type": "type:refactor", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "No timeout when sandbox timeout_seconds is 0/None",
 "body": "sandbox_executor.py:151,171-177: when config.timeout_seconds is falsy, the reader task and process.wait() have no bound; a hung scanner runs forever if the caller forgets to enforce externally.\n\nFix: require a non-zero default and warn/refuse 0.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "preexec_fn RLIMIT_AS only on Linux; macOS gets no memory cap",
 "body": "sandbox_executor.py:117 sets preexec_fn only if IS_LINUX; on macOS (the dev platform) no memory limit is applied at all.\n\nFix: document the gap and/or use a platform-appropriate mechanism.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "CLI --output writes arbitrary paths (no traversal check)",
 "body": "cli.py:126-129 does output_path.write_text(...) with no symlink/traversal guard. An absolute path or ../../ escapes the intended output dir.\n\nFix: resolve against an allowed output root and reject escapes.",
 "type": "type:security", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Workflow target re-resolved separately from validate_target (rebind gap)",
 "body": "workflows.py:153-169 validate_target (with rebind check) and engine.check_access (no rebind check) each resolve independently; the IP allowed by policy may differ from the validated one.\n\nFix: resolve once and reuse the pinned IP for both.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "custom parser declared but missing parser.py still validates",
 "body": "plugins.py:193-194 only logs a warning (doesn't fail) when output.parser=='custom' but parser.py is absent; compute_plugin_digest silently omits a non-existent parser; the plugin loads and later fails at exec.\n\nFix: fail validation when a custom parser is declared but absent.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "54 of 61 plugins omit capabilities, blocking granular denial",
 "body": "Across plugins/*/metadata.json only 7 declare capabilities; the rest rely on safety-level implication, so denying 'network' blocks all plugins and finer-grained control (filesystem, docker) is impossible for plugins that use them.\n\nFix: backfill capabilities per plugin, especially for those that write files or shell out.",
 "type": "type:refactor", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "get_plugin_check_latency_ms does O(N) subprocess spawns",
 "body": "plugins.py:700-710 calls list_plugins() which for every plugin runs shutil.which for each binary via _get_missing_binaries. As a latency probe this is expensive and repeatedly scans PATH.\n\nFix: cache binary-availability or skip it in the latency probe.",
 "type": "type:performance", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "compute_plugin_digest re-reads metadata from disk (inconsistency vs in-memory)",
 "body": "plugins.py:257 compute_plugin_digest re-parses metadata.json from disk each call; if an operator edits it after load, the in-memory plugin.checksum (from initial load) is compared against a freshly hashed on-disk file at exec, causing spurious tamper denials.\n\nFix: hash from the in-memory model consistently and document that checksum must be regenerated on edit.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "crawler has no max-redirects or response-size cap",
 "body": "crawler.py:84-150 single GET with follow_redirects=True and no max_redirects or response-size cap; can be led to large/looping redirects.\n\nFix: set max_redirects and a response-size cap.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "crawler injects extra-header values unsanitized",
 "body": "crawler.py:63-72 coerces user extra_headers values via str(value) and injects directly; header values containing CR/LF or non-HTTP tokens are not rejected.\n\nFix: validate header names/values against the HTTP token grammar.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Custom parser sandbox does not drop privileges",
 "body": "parser_sandbox.py runs the parser child with the same UID as the server. Combined with the PYTHONPATH retention (see related issue), this is a meaningful isolation gap for untrusted parser code.\n\nFix: run parser children as a dedicated low-privilege user (setuid in preexec on Linux).",
 "type": "type:security", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Plugin command templates may embed absolute paths that are non-portable",
 "body": "Several plugin metadata.json files hardcode binary names without verifying PATH; although shutil.which is used at load, no warning is surfaced at scan time if a dependency is later removed, producing an opaque exec failure.\n\nFix: surface a clear 'missing binary X' error at task creation rather than failing mid-execution.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "Wordlist/safe-mode default not surfaced when plugin omits defaults",
 "body": "When a plugin field has no 'default', the runtime uses empty string and plugins.py:_interpolate drops the whole token, silently changing the command (e.g. a flag vanishes). This can silently weaken a scan.\n\nFix: warn when a required-with-no-default field resolves empty, and document default expectations.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "Workflow scheduled tasks re-share one request id across all steps",
 "body": "workflows.py:128 captures one request_id via get_request_id() and reuses it for all steps and inside run_task. This collapses per-step tracing into a single id, hurting auditability.\n\nFix: generate a per-step request id derived from the workflow + step index.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Plugin metadata 'engine' section not validated for required keys",
 "body": "PluginMetadata.engine is Dict[str,str] but runtime _validate_plugin only loosely checks binary presence. A plugin declaring engine.type 'python' without a runner mapping passes validation yet fails at exec.\n\nFix: validate engine.type against supported runners in plugin_validator.",
 "type": "type:bug", "area": "area:plugins", "priority": "priority:low",
},

# ---------------- REPORTING / AI / RISK / NOTIF (51-68) ----------------
{
 "title": "CSV report leaks unredacted finding data (target/evidence)",
 "body": "reporting.py:1103-1120 generate_csv_report writes finding['description'], proof, target directly. Although _normalize_finding redacts some fields, target and evidence values are never redacted (see related redaction issues). CSV/HTML/PDF all leak target.\n\nFix: apply redact() to target and walk evidence values recursively.",
 "type": "type:security", "area": "area:backend", "priority": "priority:high",
},
{
 "title": "SARIF $schema and informationUri hardcode a personal repo",
 "body": "reporting.py:1241,1249 hardcode https://github.com/utksh1/SecuScan in generated SARIF artifacts. Generated artifacts should reference the project's canonical repo, not a personal handle.\n\nFix: make the base URL configurable or remove the personal reference.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "SARIF region parsing conflates host:port with file:line",
 "body": "reporting.py:1228-1234: a target like host:443 (non-URL) is treated as uri=host, startLine=443, producing a meaningless/invalid SARIF location.\n\nFix: detect host:port and either omit physicalLocation or map to a network artifact location.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Evidence values dropped from HTML/PDF reports",
 "body": "reporting.py:431,745 render 'Evidence items: {len(...)}' but never render evidence[].value. Structured evidence (which may contain secrets/URLs) is silently omitted from human-readable reports.\n\nFix: render evidence values (redacted) in the report body.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "redact_dict redacts values but leaks sensitive key names",
 "body": "redaction.py redact_dict recurses over values with redact() but never inspects keys, so a key named api_key/aws_session_token is preserved verbatim and its value may be missed by value regexes.\n\nFix: check keys against a sensitive-key set during recursive redaction.",
 "type": "type:security", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "reporting uses naive local time (generated_at) inconsistent with UTC",
 "body": "reporting.py:368 datetime.now() with no timezone, inconsistent with UTC discovered_at elsewhere. Causes off-by-timezone confusion in exported reports.\n\nFix: use timezone-aware UTC consistently (datetime.now(timezone.utc)).",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Notification dedup blocks manual re-send; failed deliveries never retried",
 "body": "notification_service.py was_already_delivered marks any prior SUCCESS as delivered (no re-send), while transient webhook failures are logged once and never retried (max_retries=0 config is unused). Security alerts can be silently lost.\n\nFix: implement retry with backoff and allow explicit re-delivery.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "send_webhook follow_redirects=False but dead redirect handling remains",
 "body": "notification_service.py:396 sets follow_redirects=False yet lines 416-444 still compute redirect handling. Harmless but dead/misleading code.\n\nFix: remove the dead redirect block.",
 "type": "type:refactor", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "AI summary generation blocks report rendering (availability risk)",
 "body": "ai_summary.py generate_summary is a synchronous-ish network call inside report rendering; if the LLM is slow/unavailable, report export hangs. No timeout per token.\n\nFix: make AI summary async with a hard timeout and a non-blocking fallback (report without summary).",
 "type": "type:performance", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "AI prompt sanitization over-redacts hostnames in titles",
 "body": "ai_summary.py:_SENSITIVE_RE replaces any multi-label hostname with [redacted], so a finding titled admin.internal.corp loses all meaning. Also misses some credential shapes. Tuning needed.\n\nFix: only redact when a sensitive-key pattern precedes the value; preserve benign hostnames.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Finding grouping logic inconsistent between two functions",
 "body": "finding_intelligence.py _stable_id('group', plugin_id, asset_id, signature) vs build_finding_groups uses _stable_id('group', title, target) ignoring asset_id. Unrelated findings with the same title+target merge, while asset-scoped grouping elsewhere does not.\n\nFix: unify grouping keys across both functions.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "fingerprint_score default 0.35 inflates confidence for unverified findings",
 "body": "finding_intelligence.py:259 unknown strength returns 0.35, so a totally unverified finding starts at ~0.24 confidence minimum regardless of evidence.\n\nFix: lower the default / make it scale with available evidence.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "knowledgebase version normalization causes false-positive CVE associations",
 "body": "knowledgebase.py:98-121 normalizes 'unknown' version to CPE ...:unknown and matches the family prefix, associating CVEs to unversioned detections (e.g. any nginx detection -> CVE-2021-23017 regardless of version).\n\nFix: do not associate version-specific CVEs when version is unknown.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "knowledgebase silently drops malformed feed files",
 "body": "knowledgebase.py:_load_entries continues on a non-list top-level feed with only a debug log; a misconfigured feed yields zero CVEs silently.\n\nFix: surface a load error/warn with the file name.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "EndpointRateLimiter sets X-RateLimit-Reset as a delta, not a timestamp",
 "body": "ratelimit.py:217,231 sets X-RateLimit-Reset = retry_after (a delta), mixing Retry-After (delta) and X-RateLimit-Reset semantics. Clients computing an absolute reset will be wrong.\n\nFix: set X-RateLimit-Reset to an epoch timestamp (or document the delta convention).",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "ConcurrentTaskLimiter.release can raise ValueError on double-release",
 "body": "ratelimit.py:102-106 running_tasks.remove(task_id) throws if the task was never acquired or already released; the exception can crash the caller.\n\nFix: use a set discard / guard the removal.",
 "type": "type:bug", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "EndpointRateLimiter memory grows unbounded under header-spoofing",
 "body": "ratelimit.py:173-189 history dict accumulates one list per identity; _cleanup_expired_identities runs only every window_seconds, so random X-Forwarded-For attacks grow memory until next cleanup. No cap on identity count.\n\nFix: cap the number of tracked identities and evict LRU.",
 "type": "type:performance", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "WorkflowRateLimiter._last_run never evicts old workflow IDs",
 "body": "ratelimit.py WorkflowRateLimiter._last_run is an unbounded dict; for long-running schedulers it grows forever.\n\nFix: add periodic eviction / cap.",
 "type": "type:performance", "area": "area:backend", "priority": "priority:low",
},

# ---------------- FRONTEND BUGS (69-88) ----------------
{
 "title": "useWebSocket: ping interval can leak across reconnects",
 "body": "useWebSocket.ts:108-193: connect() does not clear a prior ping interval before creating a new socket, so a leaked interval from a previous connection can persist. Also an auth error from the server never stops reconnect attempts (no ws.close()).\n\nFix: clear any existing ping interval at the top of connect(), and close the socket on auth error.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "useTaskSubscription SSE->polling fallback never recovers to SSE",
 "body": "useTaskSubscription.ts:177-193: once polling starts (max reconnects exceeded) there is no path back to SSE even if connectivity returns, and the error state is never cleared when polling is healthy.\n\nFix: periodically re-attempt SSE and clear error once polling is healthy.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Keyboard shortcut collision: g+s and g+h both go to scans",
 "body": "useShortcuts.ts:43,45: case 's' maps to routes.scans but 'Scanners' actually routes to routes.toolkit; g+h also maps to scans. Redundant/wrong.\n\nFix: case 's' -> routes.toolkit; keep g+h -> routes.scans (or remove duplicate).",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Escape key does not close custom popovers (Saved Views panel)",
 "body": "useShortcuts.ts:32-35: Escape is a no-op; the comment says 'could emit global event' but modals/popovers don't listen.\n\nFix: dispatch a global event and have popovers subscribe, or use focus-trapped modals.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "usePreferredExportFormat reads localStorage during render without try/catch",
 "body": "usePreferredExportFormat.ts:6-8: if localStorage is unavailable (private mode), getItem throws synchronously and the component crashes on init.\n\nFix: wrap in try/catch returning null.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "CSV export vulnerable to formula injection (CSV injection)",
 "body": "exportUtils.ts:1-8 escapeCSV does not escape leading = + - @; scanner-supplied values beginning with = execute as formulas in Excel/Sheets.\n\nFix: prefix such fields with a tab/quote or a leading apostrophe.",
 "type": "type:security", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "downloadFile revokes object URL immediately (broken on Safari)",
 "body": "exportUtils.ts:51-61 URL.revokeObjectURL(url) is called right after a.click(); in Safari the object may be revoked before the download begins, producing empty files.\n\nFix: revoke in a setTimeout (e.g. 1000ms) after click.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Export selection silently drops unloaded paginated rows",
 "body": "Findings.tsx:389-431 handleExportCSV/JSON filter findings (all loaded pages) by selectedIds; rows selected on unloaded pages are silently dropped. UI implies 'Export selected'.\n\nFix: warn or fetch all selected findings before export.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Sidebar JSON.parse on localStorage can crash the app",
 "body": "Sidebar.tsx:104-107 JSON.parse(saved) has no try/catch; corrupted localStorage crashes the Sidebar (and app via ErrorBoundary).\n\nFix: wrap in try/catch, default to true.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Sidebar toggle bound to entire aside surface (accidental collapse)",
 "body": "Sidebar.tsx:118 the whole <aside> onClick toggles isExpanded; clicking empty space collapses/expands unexpectedly.\n\nFix: move the toggle to an explicit chevron button only.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Dashboard 10s polling never backs off on error",
 "body": "Dashboard.tsx:192-229 polls every 10s forever even when backend is down; no backoff, no stop-on-error, stale summary persists.\n\nFix: stop polling after health fails and offer manual retry.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "ReportCompare only compares first 50 findings per task",
 "body": "ReportCompare.tsx:154-157 getFindings() called with no pagination (defaults page=1, perPage=50); reports with >50 findings produce incorrect diffs (missing new/fixed).\n\nFix: page through all findings or use a backend diff endpoint.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Settings.handleClearApiKey uses native window.confirm",
 "body": "Settings.tsx:225 uses blocking unstyled window.confirm(), inconsistent with the app's ConfirmModal. handleNuclearPurge wipes all secuscan* localStorage with weak confirmation.\n\nFix: use ConfirmModal and require an explicit phrase for destructive purge.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "ToolConfig integer max conflated with server timeout",
 "body": "ToolConfig.tsx:363 computes integer max as min(field.validation.max, serverLimits.sandbox.default_timeout). A port max should not be capped by timeout - likely copy/paste bug.\n\nFix: use only field.validation.max.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Workflows create form performs no step schema validation",
 "body": "Workflows.tsx:226 passes steps from JSON directly to createWorkflow with no client validation; malformed steps (missing plugin_id) fail server-side with a generic error.\n\nFix: validate each step has plugin_id before submit.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "App initial auth check renders blank (no loading state)",
 "body": "App.tsx:62-64 returns null during checkingSession, causing a blank flash. No spinner.\n\nFix: render a loading state.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "parseDateSafe only replaces first space; can produce invalid date",
 "body": "date.ts:12 raw.replace(' ', 'T') replaces only the first space; 'YYYY-MM-DD HH:MM:SS extra' becomes invalid in some engines.\n\nFix: replace all spaces or use a regex.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "formatBriefingDate result string-split in Dashboard is fragile",
 "body": "date.ts:85-98 and Dashboard.tsx:298-307 split the formatted date on ',' assuming exactly 3 segments; locale/format changes yield undefined segments.\n\nFix: return a structured object {day,month,year,time}.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "TaskDetails hook order: refs declared after useTaskSubscription",
 "body": "TaskDetails.tsx:651 calls useTaskSubscription before streamingBufferRef/rafIdRef declared at 686-688; works because unconditional but is fragile/confusing and risks future Rules-of-Hooks breakage.\n\nFix: move ref declarations above the hook call.",
 "type": "type:refactor", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Findings infinite-scroll loadMore never updates totalItems",
 "body": "Findings.tsx:645-654 totalItems is only set from the first /findings response; loadMore (604-609) doesn't update it, so filtering can make counts wrong and stop 'Load More' early.\n\nFix: update totalItems from data.total in loadMore.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "No XSS found, but i18n layer is entirely dead code",
 "body": "I18nContext.tsx exports useTranslation/t() but no page uses it; all UI strings are hardcoded English. Locale switching UI is absent despite setLocale existing.\n\nFix: wire i18n into at least one page as a pilot, or remove the unused layer.",
 "type": "type:refactor", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Scans polling can interleave overlapping fetches on page/filter change",
 "body": "Scans.tsx:115-122,163: startPolling is keyed on [filter,page]; changing page mid-poll can interleave two loadTasks sequences, and WS reloads aren't gated by page. Rapid changes cause flicker.\n\nFix: remove page from poll-effect deps and guard loadTasks with an in-flight flag.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Reports malformed generated_at yields NaN sort (no try/catch)",
 "body": "Reports.tsx:145-147 new Date(b.generated_at).getTime() with no guard; malformed value -> NaN, sorts incorrectly (treated oldest).\n\nFix: use parseDateSafe.",
 "type": "type:bug", "area": "area:frontend", "priority": "priority:low",
},

# ---------------- FEATURES / IMPROVEMENTS (89-100) ----------------
{
 "title": "Feature: Add per-plugin sandbox network namespace enforcement",
 "body": "SandboxConfig.allow_network is currently dead. Implement per-task network isolation (e.g. run scanner in a network namespace or route through the network_policy engine) so dangerous plugins can be constrained even when safe_mode is off.\n\nAcceptance: a plugin with allow_network=False cannot reach the network; unit test with a denied target.",
 "type": "type:feature", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "Feature: Centralize WebSocket + SSE base URL resolution and add reconnect backoff",
 "body": "api.ts resolveWsBase and useTaskSubscription build WS/SSE URLs inconsistently; verify the backend path (/ws/feed vs /api/v1/ws/feed). Add exponential backoff for both transports and a single source of truth for base URLs.\n\nAcceptance: WS and SSE connect using the same resolved base; backoff tested.",
 "type": "type:feature", "area": "area:frontend", "priority": "priority:medium",
},
{
 "title": "Improvement: Add a strict plugin-load mode that fails fast on bad metadata",
 "body": "Today invalid plugins are silently skipped (see related bug). Add SECUSCAN_STRICT_PLUGIN_LOAD (or --strict CLI flag) that raises on missing/corrupt metadata and surfaces a load report (loaded vs skipped with reasons).\n\nAcceptance: a missing metadata.json plugin causes a loud error in strict mode.",
 "type": "type:refactor", "area": "area:plugins", "priority": "priority:medium",
},
{
 "title": "Feature: Bulk-export findings across all pages (not just loaded)",
 "body": "Findings export currently only covers loaded pages (see related bug). Add a backend-backed export endpoint that accepts selectedIds and streams a CSV/JSON/SARIF export for all of them, honoring redaction.\n\nAcceptance: exporting 500 selected findings works without loading them client-side.",
 "type": "type:feature", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Improvement: Make AI executive summary async and non-blocking with timeout",
 "body": "Report generation blocks on the LLM call (see related bug). Move summary generation to an async task with a hard timeout and a graceful 'summary unavailable' fallback so report export never hangs.\n\nAcceptance: a 30s LLM stall does not block the report.",
 "type": "type:performance", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Feature: Add saved-view ownership/tenant scoping and sharing",
 "body": "saved_views has no ownership check (see related security bug). Implement owner scoping and add an optional 'shared' flag so teams can publish views without the IDOR risk.\n\nAcceptance: user A cannot modify/delete user B's private view; shared views are read-only to others.",
 "type": "type:feature", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Improvement: Standardize timezone handling (UTC everywhere) in API + reports",
 "body": "Mix of naive local time (reporting) and UTC (findings) causes off-by-timezone bugs. Standardize on timezone-aware UTC in the backend and pass ISO-8601 with offset to the frontend.\n\nAcceptance: generated_at and discovered_at render consistently across timezones.",
 "type": "type:refactor", "area": "area:backend", "priority": "priority:low",
},
{
 "title": "Feature: Add a plugin 'dry run' mode that prints the resolved command without executing",
 "body": "Operators cannot see the exact argv a plugin will run (including interpolated fields and resolved wordlists). Add a --dry-run that prints the final command + env after validation/sandbox resolution.\n\nAcceptance: secuscan run <plugin> --dry-run prints the command and exits 0 without side effects.",
 "type": "type:feature", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "Improvement: Add end-to-end tests for network_policy + rate limiter under Redis down",
 "body": "The scan rate limiter fails open on Redis errors with no test coverage; network_policy default-allow and rebind gaps are untested. Add integration tests covering: Redis-down (assert configurable fail-open/closed), DNS-rebinding, and metadata-IP blocking.\n\nAcceptance: tests exist and document the fail-open behavior explicitly.",
 "type": "type:testing", "area": "area:backend", "priority": "priority:medium",
},
{
 "title": "Feature: Keyboard-accessible command palette and consistent shortcut map",
 "body": "useShortcuts has collisions (see related bug) and Escape doesn't close popovers. Add a command palette (Cmd/Ctrl+K) and a single documented shortcut map; ensure all shortcuts are collapsible/conflict-free and Escape closes popovers.\n\nAcceptance: Cmd+K opens palette; no duplicate bindings; Escape closes Saved Views panel.",
 "type": "type:feature", "area": "area:frontend", "priority": "priority:low",
},
{
 "title": "Improvement: Add 'good first issue' tagging + minimal reproduction for plugin validator gaps",
 "body": "Several plugin_validator gaps (placeholder-in-if, schema mismatch, unused validation block) are well-scoped and beginner-friendly. Add unit tests that assert the validator catches each case, and label them good first issue.\n\nAcceptance: validator tests cover --if placeholders and field-type mismatch.",
 "type": "type:testing", "area": "area:plugins", "priority": "priority:low",
},
{
 "title": "Feature: Add report diff API so the frontend doesn't page 50 findings",
 "body": "ReportCompare only compares the first 50 findings (see related bug) because the frontend pages. Add a backend /reports/diff endpoint that computes new/fixed/changed across two task reports server-side.\n\nAcceptance: diff of two 500-finding reports is correct and fast.",
 "type": "type:feature", "area": "area:backend", "priority": "priority:medium",
},
]

# ----- Difficulty + good-first-issue tagging (repo uses level:* for scoring) -----
# 0-based index -> (level, good_first)
_LEVEL = {}
_GFI = set()
def _tag(i, level, gfi=False):
    _LEVEL[i] = level
    if gfi: _GFI.add(i)

# Beginner-friendly / well-scoped (level:beginner + good first issue)
for i in [5,15,21,25,27,28,34,35,36,39,44,47,49,50,52,55,56,57,58,60,62,63,64,65,67,68,71,73,77,80,83,84,88,89,95,97,98,99,100,101]:
    _tag(i, "level:beginner", gfi=True)
# Intermediate
for i in [1,2,3,4,6,7,8,9,10,11,12,13,14,16,17,18,19,20,22,23,24,26,29,30,31,32,33,37,38,40,41,42,43,45,46,48,51,53,54,59,61,66,69,70,72,74,75,76,78,79,81,82,85,86,87,90,91,92,93,94,96]:
    _tag(i, "level:intermediate")
# Advanced (security-isolation, cross-platform, protocol-level)
for i in [0, 21, 30, 31, 32, 33, 34]:
    pass  # keep advanced separate below
_ADV = {0, 29, 30, 31, 32, 33, 41, 42, 60}
for i in _ADV:
    _LEVEL[i] = "level:advanced"

for i, iss in enumerate(ISSUES):
    iss["level"] = _LEVEL.get(i, "level:intermediate")
    if i in _GFI:
        iss["gfi"] = True

def build_type_labels(iss):
    t = iss.get("type")
    extra = []
    if t == "type:security":
        extra.append("type:bug")
    if t == "type:performance":
        extra.append("type:refactor")
    return [t] + extra

if __name__ == "__main__":
    print(len(ISSUES))
