# Workflow Scheduler

The workflow scheduler is the component that runs scheduled, multi-step scans
on a timer. It is implemented by `backend/secuscan/workflows.py` and exposed
as the module-level singleton `WorkflowScheduler` (`scheduler`).

This document describes the scheduler's lifecycle, the order of checks
performed for each step, the operator-tunable environment variables, and a
short troubleshooting checklist.

## Lifecycle

The scheduler runs an asyncio background loop that wakes up every
`asyncio.sleep(5)` seconds and calls `tick()`. The loop is started and
stopped by `start()` and `stop()` on the `WorkflowScheduler` instance.

```python
from backend.secuscan.workflows import scheduler

await scheduler.start()    # idempotent; safe to call multiple times
...
await scheduler.stop()     # cancels the running task
```

`start()` is a no-op if the background task is already running. `stop()`
cancels the running task and awaits it. If the task raises `CancelledError`
during shutdown it is swallowed.

## Tick logic

Each `tick()` performs the following actions:

1. Query the `workflows` table for rows where
   `enabled = 1 AND schedule_seconds IS NOT NULL AND schedule_seconds > 0`.
2. For each row, call `_should_run(now, last_run_at, schedule_seconds)` to
   decide whether the schedule interval has elapsed since the last run.
3. If yes, call `workflow_rate_limiter.check_workflow_rate_limit(...)` to
   enforce the per-workflow minimum interval (see below).
4. If allowed, call `_run_workflow(workflow_id, steps)` which processes the
   workflow's steps in order.
5. After the workflow has finished, update `workflows.last_run_at =
   datetime('now')`.

### `_should_run` semantics

`_should_run` accepts the workflow's `last_run_at` string and a
`schedule_seconds` integer. It returns `True` when:

- `last_run_at` is `None` or empty (first-ever run), or
- the elapsed time since `last_run_at` is greater than or equal to
  `schedule_seconds`.

The function tolerates SQLite's `datetime('now')` output format
(`"2026-05-25 08:02:28"`) which lacks a timezone suffix. Naive datetimes
are treated as UTC.

## Per-step execution

Inside `_run_workflow`, each step is processed in declaration order. The
order of checks per step is:

1. **Workflow rate limit** — `_check_workflow_rate_limit(workflow_id,
   settings.workflow_min_interval_seconds)`. If the workflow has run more
   recently than the configured minimum interval, the step is skipped and
   a warning is logged. Default interval: 60 seconds.

2. **Target validation** — If the step supplies a `target` input, the
   scheduler calls `validate_target(target, safe_mode)` (in a worker thread
   bounded by `settings.dns_resolution_timeout_seconds`). Invalid targets
   are skipped with a warning.

3. **Network policy** — If `settings.enforce_network_policy` is `True`,
   the resolved target is checked against the `NetworkPolicyEngine`.
   Violations cause the step to be skipped.

4. **Plugin rate limit** — `rate_limiter.can_execute(plugin_id, max_per_hour,
   client_id=f"user:{DEFAULT_OWNER_ID}")` where `max_per_hour` is read from
   the plugin metadata's `safety.rate_limit.max_per_hour` and falls back to
   `settings.max_tasks_per_hour`. The default is 50 tasks per hour.

5. **Concurrency limit** — `concurrent_limiter.acquire(task_id)` enforces
   the maximum number of tasks running simultaneously. If the limit is
   reached, the task is marked as failed with the reason
   `"Concurrency limit reached"`.

6. **Task creation and execution** — `executor.create_task(...)` is called
   to persist the task, then `asyncio.create_task(executor.execute_task(...))`
   is launched in the background.

Step-level errors (rate limit, validation, network policy) are logged as
warnings and the workflow continues with the next step. The workflow itself
is only aborted when `create_task` or `execute_task` raises.

## Configuration

| Environment variable | Default | Description |
| --- | --- | --- |
| `SECUSCAN_WORKFLOW_MIN_INTERVAL_SECONDS` | 60 | Minimum seconds between two consecutive runs of the same workflow. |
| `SECUSCAN_MAX_TASKS_PER_HOUR` | 50 | Default per-plugin hourly rate limit when a plugin does not declare its own. |
| `SECUSCAN_MAX_CONCURRENT_TASKS` | 3 | Maximum number of tasks that may be running simultaneously across the whole backend. |
| `SECUSCAN_ENFORCE_NETWORK_POLICY` | false | If `true`, every workflow step's target is checked against the `NetworkPolicyEngine` before being scheduled. |
| `SECUSCAN_DNS_RESOLUTION_TIMEOUT_SECONDS` | 5 | Maximum wall-clock seconds a target validation / network policy check may block on DNS resolution. |
| `SECUSCAN_SAFE_MODE_DEFAULT` | true | Default safe mode setting for workflow steps that do not supply their own. |

All settings are read at scheduler-tick time, so changes to the environment
take effect on the next tick (≤ 5 seconds).

## Workflow row format

Workflows live in the `workflows` table:

| Column | Type | Description |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | Workflow identifier (UUID). |
| `name` | TEXT | Human-readable workflow name. |
| `enabled` | INTEGER (0/1) | Whether the workflow is eligible for the tick loop. |
| `schedule_seconds` | INTEGER NULL | Interval in seconds between runs; `NULL` or `0` disables scheduled runs. |
| `last_run_at` | TEXT NULL | SQLite `datetime('now')` string of the last run. |
| `steps_json` | TEXT NULL | JSON array of step objects (see below). |

### Step object

Each entry in `steps_json` is a dict with the following keys:

```json
{
  "plugin_id": "nmap",
  "inputs": {
    "target": "10.0.0.1",
    "ports": "1-1000"
  },
  "execution_context": {
    "scan_profile": "standard",
    "validation_mode": "detect_only",
    "evidence_level": "standard"
  },
  "preset": "standard"
}
```

`plugin_id` is required. `inputs`, `execution_context`, and `preset` are
optional. `safe_mode` in `inputs` is overwritten by the scheduler with the
value computed from the workflow's target policy (or the global default).

## Troubleshooting

**The workflow never runs.**

- Check that `enabled = 1` and `schedule_seconds > 0` in the `workflows`
  row.
- Check the application logs for a "Workflow scheduler started" message —
  if it is missing, `await scheduler.start()` was never called.
- Check the application logs for "Workflow scheduler tick failed" — a DB
  error in the tick loop is logged and the loop continues, but no
  workflows will be processed until the underlying error is fixed.

**The workflow runs on every tick.**

- `_should_run` returns `True` when `last_run_at` is `None`. The first
  tick after a row is inserted will always schedule the workflow. Verify
  that the subsequent UPDATE statement is succeeding — check the DB for
  a recent `last_run_at`.
- If `schedule_seconds` is `1` and the workflow takes longer than 1 second
  to run, the next tick will see `last_run_at` older than `schedule_seconds`
  and schedule it again. Use a larger `schedule_seconds` value or rely on
  the per-workflow rate limit (see below).

**The workflow is skipped with "rate limited".**

- The per-workflow rate limit is enforced by
  `workflow_rate_limiter.check_workflow_rate_limit(workflow_id,
  settings.workflow_min_interval_seconds)`. Increase
  `SECUSCAN_WORKFLOW_MIN_INTERVAL_SECONDS` to allow more frequent runs.

**The workflow is skipped with "target validation failed".**

- The step's target did not pass `validate_target`. In safe mode, the
  target must resolve to a private IP (RFC 1918) or a network in
  `SECUSCAN_ALLOWED_NETWORKS`. Public IPs and CIDR ranges are blocked.

**The task fails with "Concurrency limit reached".**

- The `concurrent_limiter` is shared with the user-facing
  `/api/v1/task/start` endpoint. Increase
  `SECUSCAN_MAX_CONCURRENT_TASKS` or stagger workflow steps to avoid
  running too many tasks at once.

**The task fails with "rate limit exceeded for <plugin>".**

- The plugin's per-hour quota is exhausted. Either wait for the hour to
  roll over, or raise the plugin's `safety.rate_limit.max_per_hour` in
  its `metadata.json`.

## Example

A minimal workflow that scans `10.0.0.1` with `nmap` every hour:

```python
import asyncio
import json
import uuid

from backend.secuscan.database import get_db
from backend.secuscan.workflows import scheduler


async def seed_workflow():
    db = await get_db()
    workflow_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO workflows (
            id, name, enabled, schedule_seconds, steps_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            workflow_id,
            "Hourly internal nmap scan",
            1,
            3600,
            json.dumps([
                {
                    "plugin_id": "nmap",
                    "inputs": {"target": "10.0.0.1", "ports": "22,80,443"},
                    "execution_context": {
                        "scan_profile": "standard",
                        "validation_mode": "detect_only",
                        "evidence_level": "standard",
                    },
                }
            ]),
        ),
    )
    return workflow_id


async def main():
    workflow_id = await seed_workflow()
    print(f"Created workflow {workflow_id}")
    await scheduler.start()
    try:
        # Run forever; the scheduler tick is in the background.
        await asyncio.Event().wait()
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
```
