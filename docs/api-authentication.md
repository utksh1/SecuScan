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

The key is stored in the browser's `localStorage` under `secuscan_api_key` and
sent automatically on every subsequent API request via the `X-Api-Key` header.
No server-side session or cookie is involved — only the operator's browser retains
the key.

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

## Security considerations

- The key file is written with mode `0600` so only the process owner can read it.
- Key comparison uses `secrets.compare_digest` to prevent timing-oracle attacks.
- There is no unauthenticated endpoint that exposes the key over the network.
  The only way to retrieve the key is to read the file from the filesystem where
  the backend is running — which requires local access to that machine.
- If the backend is not yet initialised (key file missing and startup not complete),
  protected routes return `HTTP 503` rather than `401` to distinguish between
  an uninitialised service and a bad credential.
- API keys should never be transmitted to third-party webhook destinations.
- Operators should avoid embedding API credentials in webhook payloads, query parameters, or callback URLs.
- When webhook integrations are used, restrict outbound destinations to trusted services and use HTTPS for all webhook traffic.
- Webhook endpoints should be reviewed periodically to reduce SSRF exposure and accidental data disclosure risks.
