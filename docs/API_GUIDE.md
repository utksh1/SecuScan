# API Guide

## Overview

SecuScan exposes backend APIs using FastAPI.

API documentation becomes available after backend startup:

```text
http://127.0.0.1:8000/docs
```

---

# Example API Workflow

## Start Scan

Example request:

```bash
curl -X POST http://127.0.0.1:8000/api/scan \
-H "Content-Type: application/json" \
-d '{"target":"example.com"}'
```

---

# Example Response

```json
{
  "status": "started",
  "task_id": "12345"
}
```

---

# Error Handling

Typical API errors include:

- Invalid payload
- Missing parameters
- Unsupported plugin
- Internal execution errors

---

# Frontend Integration Notes

Frontend components communicate with backend APIs using HTTP requests and render scan results dynamically.