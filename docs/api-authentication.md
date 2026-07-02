# API Authentication

All `/api/v1/*` routes require a valid API key. The only unauthenticated endpoints
are `/` (API info) and `/api/v1/health` (health checks).

## How the key is generated

On first startup the backend generates a cryptographically random 64-character hex key,
writes it to `<data_dir>/.api_key` (mode `0600`), and prints it to the console:

```
✓ API key authentication ready (key file: backend/data/.api_key)
```

On every subsequent start the same key is loaded from the file.

To rotate the key, delete the file and restart the backend:

```bash
rm backend/data/.api_key
python -m secuscan   # a new key is generated on startup
```

## Frontend / UI

The web UI does **not** fetch the key from the backend. You must configure it
manually once after starting the backend:

1. Read the key from the key file:
   ```bash
   cat backend/data/.api_key
   ```
2. Open the SecuScan UI → **Settings** → **API Key** section.
3. Paste the key into the **Backend API Key** field and click **Save**.

The UI validates the key by calling `POST /api/v1/auth/session`. On success, the
backend sets a signed `secuscan_session` cookie with the `HttpOnly` flag. The raw
API key is kept only in frontend memory while the page is open; it is **not**
persisted to `localStorage`.

After a successful login, normal browser requests authenticate with the session
cookie. Direct API clients and scripts should continue to send `X-Api-Key` or
`Authorization: Bearer` headers as shown below.

The browser session currently expires after one hour. Logging out or clearing the
API key in Settings calls `POST /api/v1/auth/session/logout`, clears the cookie,
and drops the in-memory key.

## External / scripted access

Read the key from the file and pass it in either of two header formats:

```bash
API_KEY=$(cat backend/data/.api_key)

# Option A — X-Api-Key header
curl -H "X-Api-Key: $API_KEY" http://localhost:8000/api/v1/plugins

# Option B — Bearer token
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/plugins
```

## Environment variable override

Set `SECUSCAN_API_KEY_FILE` to point to a different key file path if you need to
store the key outside the default data directory:

```bash
export SECUSCAN_API_KEY_FILE=/run/secrets/secuscan_api_key
python -m secuscan
```

## Unauthenticated endpoints

| Path | Reason |
|---|---|
| `GET /` | API info / root |
| `GET /api/v1/health` | Health checks and monitoring |

All other `/api/v1/*` routes require a valid `X-Api-Key` or `Authorization: Bearer`
header. Requests without a valid key receive `HTTP 401`.

## Owner Scoping and Multi-Workspace Isolation

SecuScan uses a two-layer model for request identity:

1. **Authentication** — the shared deployment API key (via `X-Api-Key` or `Authorization: Bearer`)
   proves the caller is a valid SecuScan operator.
2. **Authorization / Owner Scoping** — the `X-User-Id` header identifies which
   workspace/user owns the data being accessed.

### How Owner Scoping Works

The `X-User-Id` HTTP header is the primary mechanism for multi-workspace isolation.
When present, `resolve_owner_id()` in `auth.py` transforms it into a stable owner
identity:

```
X-User-Id: alice  →  owner_id = "user:alice"
```

This `owner_id` is persisted on every task, finding, and report at creation time,
and compared on every read/delete operation. Without the header, all data belongs
to the single shared `default` workspace (`owner_id = "default"`).

### Resolution Logic

`resolve_owner_id(request)` applies these rules in priority order:

| Condition | Resulting `owner_id` |
|-----------|----------------------|
| `X-User-Id` header present and non-empty | `"user:" + header_value` (whitespace trimmed) |
| `X-User-Id` header missing or empty | `"default"` |

The header value is not used verbatim — it is always prefixed with `"user:"` to
prevent confusion with the default owner. This prefix also makes it easy to
distinguish user-scoped data from system-scoped data in database queries.

### Example: Isolating Two Workspaces

```bash
# Alices workspace — only sees her tasks and findings
curl -H "X-Api-Key: $API_KEY" \
     -H "X-User-Id: alice" \
     http://localhost:8000/api/v1/tasks

# Bobs workspace — only sees his tasks and findings
curl -H "X-Api-Key: $API_KEY" \
     -H "X-User-Id: bob" \
     http://localhost:8000/api/v1/tasks
```

Both calls use the same shared API key for authentication. The `X-User-Id`
header drives the data isolation.

### Security Note for Deployments

**The `X-User-Id` header must be set by a trusted upstream auth proxy (SSO, API
gateway, or similar) before requests reach SecuScan.** SecuScan itself does not
validate or authenticate this header — it trusts the value blindly. In a
single-user or air-gapped deployment, omit the header entirely to use the
default shared workspace.

This design protects against BOLA (Broken Object Level Authorization) by
ensuring that even if an operator guesses another users task or report ID,
the query is filtered by `owner_id` and returns nothing if the IDs do not
match the authenticated workspace.

### Relationship to the API Key

| Aspect | API Key (`X-Api-Key`) | `X-User-Id` |
|--------|----------------------|-------------|
| Purpose | Authenticates the deployment operator | Identifies the data owner |
| Scope | Global — valid for the entire deployment | Per-request — filters data |
| Generated by | SecuScan (64-char hex, persisted) | Upstream auth proxy |
| Default | Required for all `/api/v1/*` routes | Absent = `"default"` workspace |

### Resources covered and the 404-vs-403 rule

Owner scoping is not limited to tasks, findings, and reports. The same `owner_id`
gate also protects **workflows** and **notification rules** (issue #961). The columns
were introduced in `backend/secuscan/migrations/003_add_owner_id.sql` (issue #401).

List endpoints filter in SQL (`... WHERE owner_id = ?`), so a caller's list never
contains another owner's rows. Single-object task endpoints go through the
`require_owned_task` helper in `backend/secuscan/routes.py`, which deliberately
separates two failure modes:

| Situation | Status |
|---|---|
| Object does not exist at all | `404 Not Found` |
| Object exists but is owned by someone else | `403 Forbidden` |

Either way the object's contents are never returned to a non-owner. Keeping the two
codes distinct makes the "exists but forbidden" case observable and testable.

### Why tests must cover cross-owner access

An owner check is easy to add to one endpoint and forget on the next, and a single
unscoped query silently re-opens the BOLA hole. So every owner-scoped endpoint needs
a test proving a **second** user is *refused* — not merely that the owner succeeds.
The existing suites are the template to copy when adding an endpoint:

- `testing/backend/integration/test_owner_authorization.py` — tasks / findings /
  reports: list scoping, per-object `403`, missing-object `404`, and bulk-delete /
  clear only ever touching the caller's own rows.
- `testing/backend/integration/test_workflow_owner_bola.py` — workflows and
  notification rules.
- `testing/backend/unit/test_auth_owner_resolution.py` — the header → `owner_id`
  resolution itself.

A new owner-scoped endpoint is not "done" until a cross-owner test asserts the
non-owner gets `403` (or, for a list endpoint, simply does not see the row). Run the
suites with:

```bash
pytest testing/backend/integration/test_owner_authorization.py \
       testing/backend/integration/test_workflow_owner_bola.py \
       testing/backend/unit/test_auth_owner_resolution.py -q
```

## Security considerations

- The key file is written with mode `0600` so only the process owner can read it.
- Key comparison uses `secrets.compare_digest` to prevent timing-oracle attacks.
- There is no unauthenticated endpoint that exposes the key over the network.
  The only way to retrieve the key is to read the file from the filesystem where
  the backend is running — which requires local access to that machine.
- The web UI uses an HttpOnly signed session cookie after the first successful
  API-key validation so the raw key does not need to persist in browser storage.
- If the backend is not yet initialised (key file missing and startup not complete),
  protected routes return `HTTP 503` rather than `401` to distinguish between
  an uninitialised service and a bad credential.
- API keys should never be transmitted to third-party webhook destinations.
- Operators should avoid embedding API credentials in webhook payloads, query parameters, or callback URLs.
- When webhook integrations are used, restrict outbound destinations to trusted services and use HTTPS for all webhook traffic.
- Webhook endpoints should be reviewed periodically to reduce SSRF exposure and accidental data disclosure risks.
