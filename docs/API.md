# SecuScan API Documentation

## Tasks API

### List Tasks with Pagination

**Endpoint:** `GET /api/v1/tasks`

**Description:** Returns a paginated list of all scan tasks with navigation metadata.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| page | integer | No | 1 | Page number (1-indexed) |
| per_page | integer | No | 25 | Items per page (1-100) |
| plugin_id | string | No | null | Filter by plugin ID |
| status | string | No | null | Filter by status |

**Response (200 OK):**

```json
{
  "tasks": [...],
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total_pages": 4,
    "total_items": 87,
    "next": "/api/v1/tasks?page=2&per_page=25",
    "previous": null
  }
}



"""
# Basic pagination
curl "http://localhost:8000/api/v1/tasks?page=2&per_page=10"

# With filters
curl "http://localhost:8000/api/v1/tasks?status=completed&plugin_id=nmap&page=1&per_page=20"
"""

## Endpoint Rate Limits

SecuScan applies independent rate-limit buckets per client identity. Identity is resolved from `X-API-Key`, then bearer authorization, then the direct client IP.

Default buckets:

| Bucket | Endpoints | Default |
|--------|-----------|---------|
| `task_start` | `POST /api/v1/task/start` | 20 requests / 60 seconds |
| `vault` | `/api/v1/vault*` | 30 requests / 60 seconds |
| `report_download` | `/api/v1/task/{task_id}/report/{format}` | 60 requests / 60 seconds |
| `read_heavy` | `/api/v1/tasks`, `/api/v1/findings`, `/api/v1/reports`, `/api/v1/dashboard/summary` | 120 requests / 60 seconds |

Every limited response includes:

```text
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 19
X-RateLimit-Reset: 1780000000
```

When a bucket is exhausted, SecuScan returns `429 Too Many Requests` with `Retry-After`:

```json
{
  "detail": {
    "error": "rate_limit_exceeded",
    "bucket": "task_start",
    "message": "Too many requests for this endpoint bucket."
  }
}
```

Operators can tune limits with environment variables:

```bash
SECUSCAN_ENDPOINT_RATE_LIMIT_WINDOW_SECONDS=60
SECUSCAN_TASK_START_RATE_LIMIT=20
SECUSCAN_VAULT_RATE_LIMIT=30
SECUSCAN_REPORT_DOWNLOAD_RATE_LIMIT=60
SECUSCAN_READ_HEAVY_RATE_LIMIT=120
```
