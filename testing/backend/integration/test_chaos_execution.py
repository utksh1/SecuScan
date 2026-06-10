"""
Chaos tests for task execution failure modes.
Issue #259 — Add chaos tests for task execution failures and partial artifacts.

Scenarios covered
-----------------
1. Subprocess crash (OSError raised by _execute_command)
   → task must land on status='failed', not 'running' or 'completed'.

2. Report upsert failure after a successful command run
   → even though the command exited cleanly and the happy-path UPDATE already
     wrote status='completed', the subsequent except block must overwrite that
     with status='failed'. No misleading success record may survive.

3. Non-zero subprocess exit with a raw artifact written to disk
   → a raw output file on disk is a debugging aid, not a success signal.
     The task must be 'failed' and the report record must also be 'failed'.

4. Concurrency slot released unconditionally after a crash
   → the finally block in execute_task must always call
     concurrent_limiter.release(task_id) so a crashed task can never
     permanently occupy a concurrency slot and starve subsequent scans.

Design constraints
------------------
- All failure injection via unittest.mock.patch / patch.object at
  well-defined seams.  No real subprocesses, no network I/O, no sleep/timing.
  Tests are fully deterministic.
- Each test uses a fresh isolated SQLite database and in-memory cache,
  provided by the autouse setup_test_environment fixture in conftest.py.
- Tests call TaskExecutor.execute_task() directly; no HTTP layer is involved.
- The icmp_ping plugin is used because it is a simple CLI plugin (binary: ping)
  that builds a real command from {target} and is consistently loaded in all
  test runs via the existing conftest settings.
"""

import asyncio
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def chaos_env(setup_test_environment):
    """
    Provide an isolated executor environment on top of the already-monkeypatched
    settings supplied by the autouse setup_test_environment conftest fixture.

    Sets up:
      - fresh SQLite DB (schema created by init_db)
      - fresh in-memory cache (init_cache, no Redis)
      - full plugin registry (init_plugins pointing at the project plugins/ dir)
      - a TaskExecutor instance with no pre-existing running tasks
      - rate-limiter / concurrent-limiter state reset

    Yields a plain dict so individual tests can access the executor, db, and
    the path to the raw output directory without importing anything themselves.
    """
    from backend.secuscan.config import settings
    from backend.secuscan import database as db_module
    from backend.secuscan import cache as cache_module
    from backend.secuscan.plugins import init_plugins
    from backend.secuscan.executor import TaskExecutor
    from backend.secuscan.ratelimit import concurrent_limiter, rate_limiter

    # Reset shared rate-limiter state that might bleed across tests.
    await rate_limiter.reset()
    async with concurrent_limiter.lock:
        concurrent_limiter.running_tasks.clear()

    # Initialise the DB, cache, and plugin registry against the already-
    # monkeypatched settings paths (setup_test_environment handles those).
    test_db = await db_module.init_db(settings.database_path)
    await cache_module.init_cache()
    await init_plugins(settings.plugins_dir)

    executor = TaskExecutor()

    yield {
        "executor": executor,
        "db": test_db,
        "db_path": settings.database_path,
        "raw_dir": Path(settings.raw_output_dir),
    }

    # Teardown: disconnect cleanly so the next test starts with a blank slate.
    await test_db.disconnect()
    db_module.db = None
    if cache_module.cache is not None:
        await cache_module.cache.disconnect()
        cache_module.cache = None


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _insert_queued_task(
    db,
    plugin_id: str = "icmp_ping",
    inputs: dict | None = None,
) -> str:
    """Insert a minimal task row in 'queued' state and return its ID.

    execute_task() reads plugin_id and inputs_json from the DB when it starts,
    so they must be consistent with a real loaded plugin.  icmp_ping is chosen
    because it is simple (binary: ping, one required field: target) and its
    command_template resolves cleanly from {"target": "127.0.0.1"}.
    """
    if inputs is None:
        inputs = {"target": "127.0.0.1"}
    task_id = str(uuid.uuid4())
    await db.execute(
        "INSERT INTO tasks "
        "(id, plugin_id, tool_name, target, inputs_json, status, consent_granted) "
        "VALUES (?, ?, 'ICMP Ping', '127.0.0.1', ?, 'queued', 1)",
        (task_id, plugin_id, json.dumps(inputs)),
    )
    return task_id


# ---------------------------------------------------------------------------
# Read-back helpers (open a second connection so tests see committed data)
# ---------------------------------------------------------------------------

async def _read_task(db_path: str, task_id: str) -> dict:
    """Return the relevant columns for one task row, or {} if not found."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT status, error_message, raw_output_path FROM tasks WHERE id = ?",
            (task_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


async def _read_report(db_path: str, task_id: str) -> dict:
    """Return the report row for a task, or {} if none was written."""
    async with aiosqlite.connect(db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(
            "SELECT status FROM reports WHERE task_id = ?",
            (task_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Test 1 — subprocess crash → status='failed', task removed from running_tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_crash_marks_task_failed(chaos_env):
    """
    When _execute_command raises OSError (e.g., the binary is gone, OOM kill,
    broken pipe), execute_task must:
      a) catch the exception without re-raising it to the caller,
      b) write status='failed' and a non-empty error_message to the DB,
      c) remove the task from executor.running_tasks via the finally block.

    The task must never be left in 'running' state after the coroutine returns.
    """
    executor = chaos_env["executor"]
    db       = chaos_env["db"]
    db_path  = chaos_env["db_path"]

    task_id = await _insert_queued_task(db)

    # Replace _execute_command entirely so the OSError propagates directly into
    # execute_task's try block — bypassing the method's own inner try/except.
    with patch.object(
        executor,
        "_execute_command",
        new_callable=AsyncMock,
        side_effect=OSError("simulated: binary not found"),
    ):
        # Must not raise; execute_task swallows Exception subclasses.
        await executor.execute_task(task_id)

    row = await _read_task(db_path, task_id)

    assert row["status"] == "failed", (
        f"Process crash must leave status='failed', got '{row['status']}'"
    )
    assert row["error_message"] is not None, (
        "error_message must be populated after a process crash"
    )
    assert "binary not found" in row["error_message"], (
        "error_message should contain the original exception text"
    )
    assert task_id not in executor.running_tasks, (
        "execute_task's finally block must remove the task from running_tasks"
    )


# ---------------------------------------------------------------------------
# Test 2 — upsert failure after successful scan → overwrites 'completed' → 'failed'
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_failure_after_successful_scan_marks_task_failed(chaos_env):
    """
    In execute_task's standard-plugin path the UPDATE to status='completed' is
    written BEFORE _upsert_findings_and_report is called.  If upsert raises, the
    except handler runs a second UPDATE to status='failed', overwriting the earlier
    'completed'.  This test verifies that overwrite actually happens so a mid-report
    crash never leaves a misleading 'completed' record in the database.
    """
    executor = chaos_env["executor"]
    db       = chaos_env["db"]
    db_path  = chaos_env["db_path"]

    task_id = await _insert_queued_task(db)

    # Minimal icmp_ping stdout that satisfies the nonfatal-exit-code success
    # patterns so _classify_command_result returns ("completed", None).
    ping_stdout = (
        "PING 127.0.0.1 (127.0.0.1): 56 data bytes\n"
        "--- 127.0.0.1 ping statistics ---\n"
        "4 packets transmitted, 4 received, 0% packet loss, time 3003ms\n"
    )

    with (
        patch.object(
            executor,
            "_execute_command",
            new_callable=AsyncMock,
            return_value=(ping_stdout, 0),
        ),
        patch.object(
            executor,
            "_upsert_findings_and_report",
            new_callable=AsyncMock,
            side_effect=RuntimeError("simulated DB write failure during upsert"),
        ),
    ):
        await executor.execute_task(task_id)

    row = await _read_task(db_path, task_id)

    assert row["status"] == "failed", (
        "A upsert failure after a successful command run must produce status='failed'. "
        f"The except block must overwrite the happy-path 'completed' UPDATE. "
        f"Got '{row['status']}' instead."
    )
    assert task_id not in executor.running_tasks, (
        "Task must be removed from running_tasks even when upsert fails"
    )


# ---------------------------------------------------------------------------
# Test 3 — non-zero exit + raw artifact on disk → task failed, report failed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_nonzero_exit_raw_artifact_present_task_is_failed(chaos_env):
    """
    When a subprocess exits non-zero and the output does not match any of the
    plugin's success_output_patterns, execute_task must:
      a) write the raw artifact to disk (expected — it is the debugging record),
      b) record status='failed' in the tasks table,
      c) record status='failed' in the reports table.

    The existence of a raw output file must never imply a successful scan result.
    """
    executor = chaos_env["executor"]
    db       = chaos_env["db"]
    db_path  = chaos_env["db_path"]
    raw_dir  = chaos_env["raw_dir"]

    task_id = await _insert_queued_task(db)

    # Output that does NOT contain icmp_ping's success patterns
    # ("ping statistics", "packet loss") so _classify_command_result
    # returns FAILED regardless of the nonfatal_exit_codes list.
    failure_output = (
        "ping: cannot resolve definitely-not-real-host.invalid: "
        "Name or service not known\n"
    )

    with patch.object(
        executor,
        "_execute_command",
        new_callable=AsyncMock,
        return_value=(failure_output, 2),
    ):
        await executor.execute_task(task_id)

    task_row = await _read_task(db_path, task_id)
    assert task_row["status"] == "failed", (
        "Non-zero exit without a matching success pattern must produce status='failed', "
        f"got '{task_row['status']}'"
    )

    # The raw output file is written before status classification.
    # Its presence is intentional: it holds the tool output for debugging.
    raw_file = raw_dir / f"{task_id}.txt"
    assert raw_file.exists(), (
        "Raw output file must be written to disk even for failed scans "
        "(it is the operator's debugging record)"
    )
    assert "Name or service not known" in raw_file.read_text(), (
        "Raw file content must reflect the actual tool output"
    )

    # The report row must also be marked 'failed' — not 'ready'.
    report_row = await _read_report(db_path, task_id)
    assert report_row, (
        "A report row must be inserted even for failed scans so the UI can "
        "display the failure state without a missing-row error"
    )
    assert report_row["status"] == "failed", (
        f"Report status must be 'failed' when the task failed, "
        f"got '{report_row['status']}'"
    )


# ---------------------------------------------------------------------------
# Test 4 — concurrency slot released unconditionally after crash
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrency_slot_released_after_crash(chaos_env):
    """
    In production, routes.py acquires a concurrent_limiter slot before scheduling
    execute_task as a background coroutine.  The finally block in execute_task is
    the only place that releases it.  If that release is missing or conditional,
    a crash permanently consumes a slot and all subsequent scans queue forever.

    This test injects a crash early in execute_task (before start_time is set)
    by making get_plugin_manager raise, then verifies the slot count drops by one.
    """
    from backend.secuscan.ratelimit import concurrent_limiter

    executor = chaos_env["executor"]
    db       = chaos_env["db"]
    db_path  = chaos_env["db_path"]

    task_id = await _insert_queued_task(db)

    # Simulate the slot acquisition that routes.py performs before the background
    # task is scheduled.
    async with concurrent_limiter.lock:
        concurrent_limiter.running_tasks.append(task_id)

    held_slots_before = len(concurrent_limiter.running_tasks)

    # Inject an early crash: get_plugin_manager raises before start_time is
    # assigned, which exercises the 'start_time' in locals() guard in the
    # except block as well as the finally block's slot release.
    with patch(
        "backend.secuscan.executor.get_plugin_manager",
        side_effect=RuntimeError("simulated plugin registry unavailable"),
    ):
        await executor.execute_task(task_id)

    held_slots_after = len(concurrent_limiter.running_tasks)

    assert held_slots_after == held_slots_before - 1, (
        "concurrent_limiter must release the slot in the finally block after a crash. "
        f"Held before: {held_slots_before}, held after: {held_slots_after}"
    )
    assert task_id not in concurrent_limiter.running_tasks, (
        "The crashed task's ID must not remain in concurrent_limiter.running_tasks"
    )

    # The task must also be recorded as failed, not left as 'running'.
    row = await _read_task(db_path, task_id)
    assert row["status"] == "failed", (
        f"Task status must be 'failed' after a crash, got '{row['status']}'"
    )
