# Request ID Tracing and Correlation Guide

This guide explains how request IDs are generated, propagated, and correlated across the different layers of SecuScan. If you are developing new endpoints, background tasks, or debugging system issues, refer to this guide to understand request tracing.

---

## Overview

SecuScan uses **Request IDs** to correlate actions end-to-end across:
1. **HTTP Requests**: Incoming API calls.
2. **Application Logs**: Logging output format (`JSONFormatter`).
3. **Audit Trail**: Action records saved in the database (`audit_log` table).
4. **Background Operations**: Async workflow steps and tasks.

The tracking header used throughout the system is `X-Request-ID`.

---

## 1. Generation & Context

The request ID lifecycle is managed by [request_context.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/request_context.py) using Python's standard `contextvars.ContextVar`.

- If the incoming HTTP request has an `X-Request-ID` header, that value is used verbatim.
- If no header is provided, a standard UUID (v4) is generated via `uuid.uuid4()`.

### Code Reference

```python
from secuscan.request_context import get_request_id, set_request_id

# Retrieve the current request ID
current_id = get_request_id()

# Set/override the request ID (generates a uuid4 if none provided)
new_id = set_request_id("custom-id")
```

---

## 2. Middleware Passthrough

For HTTP requests, [request_middleware.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/request_middleware.py) defines the `RequestIDMiddleware` registered in FastAPI.

During the request-response lifecycle:
1. **Extraction**: The middleware reads the `X-Request-ID` header and calls `set_request_id(request_id)`.
2. **State Storage**: It attaches the ID to FastAPI's request state: `request.state.request_id = request_id`.
3. **Response Header**: It adds the ID to the outgoing response headers: `response.headers["X-Request-ID"] = request_id`.

---

## 3. Log Correlation

SecuScan filters and formats all application logs to include the request ID:
- **Filter**: `RequestIDFilter` (in [logging_utils.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/logging_utils.py)) dynamically fetches the current ID using `get_request_id()` and attaches it to the log record as `request_id`.
- **Formatter**: `JSONFormatter` (in [logging_utils.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/logging_utils.py)) serializes the log output as a JSON string, emitting `request_id` as a top-level field.

### Sample JSON Log Line

```json
{"timestamp": "2026-06-07T05:07:37.123456Z", "level": "INFO", "request_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d", "logger": "secuscan.routes", "message": "Starting scan task for target: example.com"}
```

### Filtering Logs via CLI

To isolate all log messages associated with a single request ID:

```bash
grep '"request_id": "a1b2c3d4-..."' logs/secuscan.log | jq .
```

---

## 4. Audit Log Correlation

Critical events are permanently recorded in the SQLite database by calling `db.log_audit()` in [database.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/database.py). 

- `log_audit()` automatically reads the active Request ID from context: `request_id = request_id or get_request_id()`.
- The request ID is saved inside the `context_json` column of the `audit_log` table under the `"request_id"` key.

### Querying the Audit Log in SQLite

You can query and correlate audit trails for a specific Request ID using SQLite's JSON extension functions:

```sql
SELECT timestamp, event_type, message, context_json
FROM audit_log
WHERE json_extract(context_json, '$.request_id') = 'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d';
```

---

## 5. End-to-End Debugging Walkthrough

Follow these steps to trace a custom client request from execution to storage:

1. **Trigger Request**: Send an API request using curl with a custom `X-Request-ID` header:
   ```bash
   curl -H "X-Request-ID: debug-test-001" http://localhost:8000/api/v1/health
   ```
2. **Confirm Response Header**: Check the response headers to ensure the same ID is returned:
   ```http
   X-Request-ID: debug-test-001
   ```
3. **Filter Logs**: Search the log file to see the path of execution:
   ```bash
   grep '"request_id": "debug-test-001"' logs/secuscan.log | jq .
   ```
4. **Query Database**: Open your local SQLite instance and fetch matching audit logs:
   ```bash
   sqlite3 data/secuscan.db "SELECT timestamp, event_type, message FROM audit_log WHERE json_extract(context_json, '$.request_id') = 'debug-test-001';"
   ```

---

## 6. Guidelines for Writing New Code

### Standard Request Lifecycles
Within FastAPI request handlers, `get_request_id()` is safe to call at any time to obtain the current request ID.

### Spawning Background Tasks
Python `ContextVar` environments are inherited when creating async tasks within the same execution path. However, when spawning separate background work that detaches from the request lifecycle (e.g., using `asyncio.create_task` or queueing executors), you **must** propagate the ID manually.

Example from [workflows.py](file:///d:/GSSOC/utksh1/%23573/SecuScan/backend/secuscan/workflows.py):

```python
# 1. Capture the Request ID in the active parent scope
request_id = get_request_id()

# 2. Create the wrapper task setting the captured ID inside the new ContextVar scope
async def run_task(task_id: str) -> None:
    set_request_id(request_id)
    await executor.execute_task(task_id)

asyncio.create_task(run_task(task_id))
```

If triggering background audit events manually, you can also pass a captured ID directly to the `log_audit()` call:

```python
await db.log_audit(
    event_type="background_scan",
    message="Scan complete",
    request_id=captured_request_id
)
```
