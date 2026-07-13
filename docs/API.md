# SecuScan API Documentation

## Authentication and ownership

Every endpoint below requires the API key (`X-Api-Key` or `Authorization: Bearer`),
and every result is **owner-scoped**: list and lookup endpoints only return rows
owned by the caller, where the owner is derived from the optional `X-User-Id`
header. Requesting another owner's object returns `403 Forbidden`; a genuinely
missing object returns `404 Not Found`. See
[API Authentication → Owner Scoping and Multi-Workspace Isolation](api-authentication.md#owner-scoping-and-multi-workspace-isolation)
for how the owner is resolved and why every owner-scoped endpoint needs a
cross-owner test.

## Tasks API

### List Tasks with Pagination

**Endpoint:** `GET /api/v1/tasks`

**Description:** Returns a paginated list of the **caller's** scan tasks with
navigation metadata. The list is owner-scoped (see
[Authentication and ownership](#authentication-and-ownership)) — it never includes tasks
owned by another `X-User-Id`.

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
```

```bash
# Basic pagination
curl "http://localhost:8000/api/v1/tasks?page=2&per_page=10"

# With filters
curl "http://localhost:8000/api/v1/tasks?status=completed&plugin_id=nmap&page=1&per_page=20"
```

## Notifications API

### Update Notification Rule

**Endpoint:** `PATCH /api/v1/notifications/rules/{rule_id}`

**Description:** Updates the caller's notification rule. This endpoint uses
optimistic locking on the row's `updated_at` value to prevent silent
last-write-wins overwrites during concurrent edits.

**Success Response (200 OK):** Returns the updated rule snapshot.

**Conflict Response (409 Conflict):** Returned when another request updates the
same rule after the caller's snapshot was loaded but before its PATCH is
applied. Clients should refresh from `current_rule`, reconcile local changes,
and retry with a new request.

```json
{
  "error": "notification_rule_conflict",
  "message": "Notification rule was updated by another request. Refresh the rule and retry your changes.",
  "current_rule": {
    "id": "rule-id",
    "name": "Critical alerts",
    "severity_threshold": "high",
    "channel_type": "webhook",
    "target_url_or_email": "https://example.com/hook",
    "is_active": true,
    "created_at": "2026-06-29T07:39:22Z",
    "updated_at": "2026-06-29T07:41:05Z"
  }
}
```

## Search API

### Global Search

**Endpoint:** `GET /api/v1/search`

**Description:** Searches the caller's findings and reports by keyword. Findings
are matched against `title` and `description`; reports are matched against
`name`. Results are owner-scoped (see
[Authentication and ownership](#authentication-and-ownership)) — a search never
returns findings or reports owned by another `X-User-Id`.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| q | string | Yes | — | Search query (1-200 characters) |
| limit | integer | No | 20 | Max results per category (1-100) |

**Response (200 OK):**

```json
{
  "query": "sql injection",
  "findings": [
    {
      "id": "finding-id",
      "task_id": "task-id",
      "title": "SQL Injection in login form",
      "category": "Injection",
      "severity": "high",
      "target": "example.com",
      "discovered_at": "2026-07-01T12:00:00Z"
    }
  ],
  "reports": [
    {
      "id": "report-id",
      "task_id": "task-id",
      "name": "Q3 Security Report",
      "type": "technical",
      "generated_at": "2026-07-05T09:15:00Z"
    }
  ],
  "total": 2
}
```

```bash
curl -H "X-Api-Key: $API_KEY" \
  "http://localhost:8000/api/v1/search?q=sql+injection&limit=10"
```

## See Also

* [API Authentication](api-authentication.md) — How requests are authenticated with the API key and authorized per owner (`X-User-Id` → `owner_id`), including the cross-owner test requirement.
* [Backend Architecture](backend-architecture.md) — For a detailed overview of the backend's module structure, routing, execution engine, and scanners.
