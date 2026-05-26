# API Authentication

All `/api/v1/*` routes (except `/api/v1/health` and `/api/v1/auth/key`) require an API key.

## How the key is generated

On first startup the backend generates a cryptographically random 64-character hex key,
writes it to `<data_dir>/.api_key` (mode `0600`), and loads it from there on every
subsequent start.  The default `data_dir` is `backend/data/`.

To rotate the key, delete the file and restart the backend:

```bash
rm backend/data/.api_key
python -m secuscan   # a new key is generated on startup
```

## Frontend / UI

The built-in web UI bootstraps itself automatically. On the first API call it fetches
`GET /api/v1/auth/key` (unauthenticated), caches the key in memory, and includes it as
`X-Api-Key: <key>` on every subsequent request.  No manual configuration is required for
local use.

## External / scripted access

Read the key from the file and pass it in one of two header formats:

```bash
API_KEY=$(cat backend/data/.api_key)

# Option A — X-Api-Key header
curl -H "X-Api-Key: $API_KEY" http://localhost:8000/api/v1/plugins

# Option B — Bearer token
curl -H "Authorization: Bearer $API_KEY" http://localhost:8000/api/v1/plugins
```

## Environment variable override

Set `SECUSCAN_API_KEY_FILE` to point to a different key file path if you need to store
the key outside the default data directory:

```bash
export SECUSCAN_API_KEY_FILE=/run/secrets/secuscan_api_key
python -m secuscan
```

## Unauthenticated endpoints

| Path | Reason |
|---|---|
| `GET /` | API info / root |
| `GET /api/v1/health` | Health checks and monitoring |
| `GET /api/v1/auth/key` | UI bootstrap (local key retrieval) |

> **Note:** `/api/v1/auth/key` returns the local key in plaintext. It is intentionally
> unprotected because SecuScan is designed for local, single-operator use. If you expose
> the backend over a network, restrict access to this endpoint at the network/firewall
> level or disable it by setting `SECUSCAN_DISABLE_KEY_ENDPOINT=1`.
