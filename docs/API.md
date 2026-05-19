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