"""
Task execution engine with Docker sandboxing
"""

import asyncio
from asyncio import subprocess
import os
import signal
import base64
import uuid
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import logging
import re

_CANCEL_GRACE_SECONDS = 5

from .auth import DEFAULT_OWNER_ID
from .redaction import redact
from .cache import get_cache
from .config import settings
from .database import get_db
from .plugins import get_plugin_manager
from .models import NotificationDeliveryStatus, TaskStatus, ScanPhase
from .ratelimit import concurrent_limiter
from .risk_scoring import compute_risk_score, compute_risk_factors
from .capabilities import CapabilityEnforcer, CapabilityDeniedError, build_enforcer_from_settings
from .parser_sandbox import run_parser_in_sandbox, ParserSandboxError
from .network_policy import get_policy_engine
from .notification_service import process_task_notifications
from .execution_context import is_offensive_validation, normalize_execution_context
from .finding_intelligence import (
    build_asset_summary,
    build_finding_groups,
    build_scan_diff,
    normalize_and_correlate_findings,
)
from .platform_resources import (
    get_credential_profile,
    get_session_profile,
    get_target_policy,
    persist_crawl_run,
    replace_asset_services,
    serialize_execution_context,
)
from .vault import VaultCrypto

async def _terminate_process_group(pid: int, task_id: str, grace_seconds: int = _CANCEL_GRACE_SECONDS) -> None:
    """Send SIGTERM to the process group of *pid*, wait *grace_seconds*, then SIGKILL.

    Using a process group (via start_new_session=True on subprocess creation)
    ensures every child and grandchild spawned by the scanner receives the
    signal, leaving no orphan processes after cancellation or timeout.

    Errors are logged but never re-raised so callers can always proceed to
    update task status regardless of OS-level kill failures.
    """
    try:
        pgid = os.getpgid(pid)
    except (ProcessLookupError, PermissionError) as exc:
        logger.debug("process group for pid %d already gone: %s", pid, exc)
        return

    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError) as exc:
        logger.debug("SIGTERM to pgid %d failed (already exited?): %s", pgid, exc)
        return

    for _ in range(grace_seconds * 10):
        await asyncio.sleep(0.1)
        try:
            os.killpg(pgid, 0)
        except (ProcessLookupError, PermissionError):
            return

    try:
        os.killpg(pgid, signal.SIGKILL)
        logger.warning(
            "process group %d did not exit within %ds grace — SIGKILL sent (task %s)",
            pgid, grace_seconds, task_id,
        )
    except (ProcessLookupError, PermissionError) as exc:
        logger.debug("SIGKILL to pgid %d failed: %s", pgid, exc)


def _parse_discovered_at(finding: dict) -> Optional[datetime]:
    """Extract and parse discovered_at from a finding dict, or return current UTC time."""
    raw = finding.get("discovered_at")
    if raw:
        try:
            if isinstance(raw, str):
                return datetime.fromisoformat(raw)
            if isinstance(raw, datetime):
                return raw
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)


def _validate_risk_fields(finding: dict) -> None:
    """Validate exploitability, confidence, and asset_exposure bounds in-place."""
    exp = finding.get("exploitability")
    if exp is not None:
        if not isinstance(exp, (int, float)):
            raise ValueError(f"exploitability must be numeric, got {type(exp).__name__}")
        if exp < 0 or exp > 10:
            raise ValueError(f"exploitability must be in [0, 10], got {exp}")

    conf = finding.get("confidence")
    if conf is not None:
        if not isinstance(conf, (int, float)):
            raise ValueError(f"confidence must be numeric, got {type(conf).__name__}")
        if conf < 0 or conf > 1:
            raise ValueError(f"confidence must be in [0, 1], got {conf}")

    ae = finding.get("asset_exposure")
    if ae is not None and ae.lower() not in ("critical", "high", "medium", "low"):
        raise ValueError(f"asset_exposure must be one of critical/high/medium/low, got {ae}")

# Modular Scanners
from .scanners.port_scanner import PortScanner
from .scanners.web_scanner import WebScanner
from .scanners.recon_scanner import ReconScanner
from .scanners.network_vulnerability_scanner import NetworkVulnerabilityScanner
from .scanners.api_scanner import APIScanner
from .scanners.zap_scanner import ZAPScanner
from .scanners.xss_validation_scanner import XSSValidationScanner

MODULAR_SCANNERS = {
    "port_scanner": PortScanner,
    "web_scanner": WebScanner,
    "recon_scanner": ReconScanner,
    "network_scanner": NetworkVulnerabilityScanner,
    "api_scanner": APIScanner,
    "zap_scanner": ZAPScanner,
    "xss_exploiter": XSSValidationScanner,
}

logger = logging.getLogger(__name__)
STREAM_LISTENER_QUEUE_MAXSIZE = 100


def extract_target(inputs: Dict[str, Any]) -> str:
    """Best-effort target extraction across plugin shapes."""
    return (
        inputs.get("target")
        or inputs.get("url")
        or inputs.get("host")
        or inputs.get("domain")
        or ""
    )


def _stable_asset_id(target: str, host: Any, port: Any, protocol: Any) -> str:
    material = "||".join(
        [
            str(target or "").strip().lower(),
            str(host or "").strip().lower(),
            str(port or "").strip().lower(),
            str(protocol or "").strip().lower(),
        ]
    )
    return f"asset:{uuid.uuid5(uuid.NAMESPACE_URL, material).hex[:16]}"


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    """Read a dict/sqlite row key with a default for backward-compatible mocks."""
    if row is None:
        return default
    if isinstance(row, dict):
        return row.get(key, default)
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


class TaskExecutor:
    """Executes security scanning tasks in isolated environments"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self._process_pids: Dict[str, int] = {}
        # PubSub: Map of task_id to list of active async queues listening for output/status updates
        self._listeners: Dict[str, List[asyncio.Queue]] = {}
        self._capability_enforcer: CapabilityEnforcer = build_enforcer_from_settings()

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to a task's real-time events."""
        if task_id not in self._listeners:
            self._listeners[task_id] = []
        q = asyncio.Queue(maxsize=STREAM_LISTENER_QUEUE_MAXSIZE)
        self._listeners[task_id].append(q)
        return q

    def unsubscribe(self, task_id: str, q: asyncio.Queue):
        """Unsubscribe from a task's real-time events."""
        if task_id in self._listeners and q in self._listeners[task_id]:
            self._listeners[task_id].remove(q)
            if not self._listeners[task_id]:
                self._listeners.pop(task_id, None)

    async def _broadcast(self, task_id: str, event_type: str, data: Any):
        """Broadcast an event to all active listeners of a task."""
        if task_id in self._listeners:
            event = {"type": event_type, "data": data}
            for q in list(self._listeners[task_id]):
                self._enqueue_listener_event(task_id, q, event)

    def _enqueue_listener_event(self, task_id: str, q: asyncio.Queue, event: Dict[str, Any]):
        """Add an event to a bounded listener queue without unbounded memory growth."""
        try:
            q.put_nowait(event)
            return
        except asyncio.QueueFull:
            try:
                q.get_nowait()
            except asyncio.QueueEmpty:
                pass

        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("Dropping stream event for slow listener on task %s", task_id)
    
    async def _broadcast_phase(self, task_id: str, phase: str):
        """Broadcast a scan phase transition and persist it to the database."""
        await self._broadcast(task_id, "phase", phase)
        db = await get_db()
        await db.execute(
            "UPDATE tasks SET scan_phase = ? WHERE id = ?",
            (phase, task_id)
        )

    async def create_task(
        self,
        plugin_id: str,
        inputs: Dict[str, Any],
        safe_mode: bool,
        preset: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        consent_granted: bool = False,
        owner_id: str = DEFAULT_OWNER_ID,
    ) -> str:
        """
        Create a new scan task.

        Args:
            plugin_id: Plugin identifier
            inputs: User input values
            preset: Optional preset name
            consent_granted: Whether user granted consent
            owner_id: Owning user/workspace identity used to scope later
                access (issue #401). Defaults to the shared default owner for
                internal callers (workflows, scheduler, CLI) that are not tied
                to a request.

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())
        plugin_manager = get_plugin_manager()
        plugin = plugin_manager.get_plugin(plugin_id)
        
        if not plugin:
            raise ValueError(f"Plugin not found: {plugin_id}")
        
        # Apply preset if provided
        if preset and preset in plugin.presets:
            preset_values = plugin.presets[preset]
            # Merge preset with user inputs (user inputs take precedence)
            inputs = {**preset_values, **inputs}
        
        # Store task in database
        db = await get_db()
        await db.execute(
            """
            INSERT INTO tasks (
                id, owner_id, plugin_id, tool_name, target, inputs_json, preset,
                execution_context_json, status, scan_phase, consent_granted, safe_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                owner_id,
                plugin_id,
                plugin.name,
                extract_target(inputs),
                json.dumps(inputs),
                preset,
                serialize_execution_context(execution_context),
                TaskStatus.QUEUED.value,
                ScanPhase.QUEUED.value,
                consent_granted,
                bool(safe_mode)
            )
        )
        
        # Log audit event
        await db.log_audit(
            "task_created",
            f"Task created for {plugin.name}",
            context={
                "task_id": task_id,
                "plugin_id": plugin_id,
                "target": inputs.get("target"),
                "execution_context": normalize_execution_context(execution_context),
            },
            task_id=task_id,
            plugin_id=plugin_id
        )
        
        return task_id
    
    async def mark_task_failed(self, task_id: str, reason: str) -> None:
        """
        Mark a task as failed without running it.
        Used to roll back a created-but-unscheduled task record.

        Args:
            task_id: Task identifier
            reason: Human-readable failure reason stored as error_message
        """
        db = await get_db()
        await db.execute(
            """
            UPDATE tasks SET
                status = ?,
                completed_at = ?,
                duration_seconds = ?,
                error_message = ?
            WHERE id = ?
            """,
            (
                TaskStatus.FAILED.value,
                datetime.now().isoformat(),
                0,
                reason,
                task_id,
            )
        )
        await db.log_audit(
            "task_failed",
            f"Task rejected before execution: {reason}",
            severity="warning",
            context={"task_id": task_id, "reason": reason},
            task_id=task_id,
        )

    async def execute_task(self, task_id: str):
        """
        Execute a task asynchronously.
        
        Args:
            task_id: Task identifier
        """
        db = await get_db()
        self.running_tasks[task_id] = asyncio.current_task()

        try:
            # Update status to running
            await db.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                (TaskStatus.RUNNING.value, datetime.now().isoformat(), task_id)
            )
            await self._invalidate_cached_views()

            # Get task details
            task_row = await db.fetchone(
                "SELECT owner_id, plugin_id, inputs_json, execution_context_json, safe_mode FROM tasks WHERE id = ?",
                (task_id,)
            )

            if not task_row:
                raise ValueError(f"Task not found: {task_id}")

            owner_id = task_row["owner_id"]
            plugin_id = task_row["plugin_id"]
            inputs = json.loads(task_row["inputs_json"])
            execution_context = normalize_execution_context(
                json.loads(task_row["execution_context_json"] or "{}")
            )
            safe_mode = bool(task_row["safe_mode"])
            target = extract_target(inputs)
            inputs = await self._hydrate_inputs_with_execution_context(
                db=db,
                owner_id=owner_id,
                inputs=inputs,
                execution_context=execution_context,
            )

            # ── Safe Mode & Network policy enforcement ───────────────────────
            # Enforce Safe Mode target validation inside TaskExecutor to guarantee
            # that all execution paths (manual API, workflows, scheduled tasks) are protected.
            if target:
                plugin_manager = get_plugin_manager()
                plugin = plugin_manager.get_plugin(plugin_id)
                should_validate = True
                if plugin and plugin.category == "code":
                    should_validate = False


                # Use shared is_filesystem_target from validation to ensure
                # consistent filesystem detection across route and executor layers.
                from .validation import is_filesystem_target
                is_fs = is_filesystem_target(target)

                if should_validate and not is_fs:
                    from .validation import validate_target
                    try:
                        # Enforce safe mode validation of target address in a thread pool
                        is_valid, error_msg = await asyncio.wait_for(
                            asyncio.to_thread(validate_target, target, safe_mode),
                            timeout=float(settings.dns_resolution_timeout_seconds),
                        )
                        if not is_valid:
                            await self.mark_task_failed(
                                task_id,
                                f"Safe mode target validation failed: {error_msg}",
                            )
                            await self._broadcast(task_id, "status", TaskStatus.FAILED.value)
                            return
                    except asyncio.TimeoutError:
                        await self.mark_task_failed(
                            task_id,
                            "Target validation timed out (SecuScan Guardrail)",
                        )
                        await self._broadcast(task_id, "status", TaskStatus.FAILED.value)
                        return

            # Check before launching any scanner or subprocess.  check_access()
            # writes an audit entry on every path, so no extra logging needed.
            if target and settings.enforce_network_policy:
                engine = get_policy_engine()
                try:
                    allowed, reason, _ = await asyncio.wait_for(
                        asyncio.to_thread(
                            engine.check_access,
                            dest_ip=target,
                            plugin_id=plugin_id,
                            task_id=task_id,
                        ),
                        timeout=float(settings.dns_resolution_timeout_seconds),
                    )
                except asyncio.TimeoutError:
                    allowed, reason = False, "Network policy check timed out (DNS resolution timeout)"

                if not allowed:
                    if settings.network_policy_failure_mode == "log_only":
                        logger.warning(
                            f"[Log Only] Network policy violation allowed for {target}: {reason}"
                        )
                    else:
                        await self.mark_task_failed(
                            task_id,
                            f"Network policy denied access to {target}: {reason}",
                        )
                        await self._broadcast(task_id, "status", TaskStatus.FAILED.value)
                        return  # finally block handles running_tasks cleanup + limiter release

            # Check if this is a modular scanner or a standard plugin
            plugin_manager = get_plugin_manager()
            plugin = plugin_manager.get_plugin(plugin_id)
            if not plugin:
                raise ValueError(f"Plugin not found: {plugin_id}")

            self._capability_enforcer.check(
                plugin_id=plugin.id,
                declared=plugin.capabilities,
                safety_level=plugin.safety.get("level", "safe"),
            )

            if plugin.safety.get("level") == "exploit" and not is_offensive_validation(execution_context):
                raise ValueError(
                    "Exploit-level plugins require an execution context with validation_mode set to 'proof' or 'controlled_extract'."
                )

            if plugin_id in MODULAR_SCANNERS:
                scanner_class = MODULAR_SCANNERS[plugin_id]
                scanner = scanner_class(task_id, db, safe_mode=safe_mode)
                
                logger.info(f"Executing modular scanner {plugin_id} for task {task_id}")
                await self._broadcast(task_id, "status", TaskStatus.RUNNING.value)
                await self._broadcast_phase(task_id, ScanPhase.RUNNING_COMMAND.value)
                
                start_time = time.time()
                # Run the scanner
                result = await scanner.run(target, inputs)
                duration = time.time() - start_time
                
                # Update task with results
                final_status = TaskStatus.COMPLETED.value if result.get("status") != "failed" else TaskStatus.FAILED.value
                
                await db.execute(
                    """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        structured_json = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
                    (
                        final_status,
                        datetime.now().isoformat(),
                        duration,
                        json.dumps(result),
                        result.get("error_message"),
                        task_id
                    )
                )

                # Upsert findings and report using the scanner's result
                await self._broadcast_phase(task_id, ScanPhase.PARSING.value)
                await self._upsert_findings_and_report_from_scanner(
                    db=db,
                    task_id=task_id,
                    owner_id=owner_id,
                    scanner=scanner,
                    plugin_id=plugin_id,
                    target=target,
                    status=final_status,
                    result=result
                )
                await self._broadcast_phase(task_id, ScanPhase.REPORTING.value)

            else:
                # Standard Plugin Execution
                command = plugin_manager.build_command(plugin_id, inputs)

                if not command:
                    raise ValueError("Failed to build command")

                # Apply Docker Sandboxing if enabled
                if settings.docker_enabled:
                    # Validate the named Docker network exists before using it.
                    # If missing, attempt to create it automatically rather than failing.
                    _net_check = await asyncio.create_subprocess_exec(
                        "docker", "network", "inspect", settings.docker_network,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await _net_check.wait()
                    if _net_check.returncode != 0:
                        logger.info(f"Docker network '{settings.docker_network}' not found. Creating isolated bridge network (ICC disabled)...")
                        _net_create = await asyncio.create_subprocess_exec(
                            "docker", "network", "create",
                            "--driver", "bridge",
                            "--opt", "com.docker.network.bridge.enable_icc=false",
                            settings.docker_network,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
                        await _net_create.wait()
                        if _net_create.returncode != 0:
                            logger.warning("Failed to create isolated bridge network with ICC disabled. Falling back to standard bridge...")
                            _net_create_fallback = await asyncio.create_subprocess_exec(
                                "docker", "network", "create", "--driver", "bridge", settings.docker_network,
                                stdout=asyncio.subprocess.DEVNULL,
                                stderr=asyncio.subprocess.DEVNULL,
                            )
                            await _net_create_fallback.wait()
                            if _net_create_fallback.returncode != 0:
                                raise RuntimeError(
                                    f"Docker network '{settings.docker_network}' does not exist and could not be created automatically."
                                )
                            logger.info(f"Successfully created Docker network '{settings.docker_network}' (fallback)")
                        else:
                            logger.info(f"Successfully created Docker network '{settings.docker_network}' with ICC disabled")

                    docker_image = plugin.docker_image or "alpine:latest"
                    docker_cmd = [
                        "docker",
                        "run",
                        "--rm",
                        "--name",
                        f"secuscan_task_{task_id}",
                        "--memory",
                        f"{settings.sandbox_memory_mb}m",
                        "--cpus",
                        str(settings.sandbox_cpu_quota),
                        "--cap-drop", "NET_RAW",
                        "--network", settings.docker_network,
                        docker_image,
                    ]
                    command = docker_cmd + command

                logger.info(f"Executing task {task_id}: {' '.join(command)}")
                await self._broadcast(task_id, "status", TaskStatus.RUNNING.value)
                await self._broadcast_phase(task_id, ScanPhase.RUNNING_COMMAND.value)

                # Execute command
                start_time = time.time()
                output, exit_code = await self._execute_command(
                    command,
                    task_id,
                    timeout=self._resolve_execution_timeout(inputs),
                )
                duration = time.time() - start_time

                # Save raw output
                raw_path = Path(settings.raw_output_dir) / f"{task_id}.txt"
                output = redact(output)
                with open(raw_path, 'w') as f:
                    f.write(output)

                # Some CLI tools use non-zero exit codes for "no result" states while still
                # producing a complete, parseable report. Let plugin metadata opt into that.
                final_status, error_message = self._classify_command_result(
                    plugin=plugin,
                    output=output,
                    exit_code=exit_code,
                )

                await db.execute(
                    """
                    UPDATE tasks SET
                        status = ?,
                        completed_at = ?,
                        duration_seconds = ?,
                        exit_code = ?,
                        raw_output_path = ?,
                        command_used = ?,
                        error_message = ?
                    WHERE id = ?
                    """,
                    (
                        final_status,
                        datetime.now().isoformat(),
                        duration,
                        exit_code,
                        str(raw_path),
                        " ".join(command),
                        error_message,
                        task_id
                    )
                )

                # Upsert findings and report
                await self._broadcast_phase(task_id, ScanPhase.PARSING.value)
                await self._upsert_findings_and_report(
                    db=db,
                    task_id=task_id,
                    owner_id=owner_id,
                    plugin=plugin,
                    plugin_id=plugin_id,
                    target=target,
                    status=final_status,
                    output=output
                )
                await self._broadcast_phase(task_id, ScanPhase.REPORTING.value)

            await self._dispatch_task_notifications(db, task_id)

            await self._broadcast_phase(task_id, ScanPhase.FINISHED.value)
            await self._broadcast(task_id, "status", final_status)
            await self._invalidate_cached_views()

            # Log completion
            await db.log_audit(
                "task_completed",
                f"Task completed in {duration:.2f}s",
                context={"task_id": task_id, "exit_code": locals().get('exit_code', 0)},
                task_id=task_id,
                plugin_id=plugin_id
            )

            logger.info(f"Task {task_id} completed in {duration:.2f}s")

        except asyncio.CancelledError:
            # CancelledError inherits from BaseException, not Exception —
            # it bypasses the broad except below, so we handle it explicitly.
            # Task.cancelled() returns False while the finally block is still
            # executing, so this is the only reliable place to write the
            # cancellation status to the DB.
            duration = (time.time() - start_time) if 'start_time' in locals() else 0
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?
                WHERE id = ? AND status = ?
                """,
                (
                    TaskStatus.CANCELLED.value,
                    datetime.now().isoformat(),
                    duration,
                    task_id,
                    TaskStatus.RUNNING.value,
                )
            )
            await self._broadcast(task_id, "status", TaskStatus.CANCELLED.value)
            await self._invalidate_cached_views()
            raise  # let asyncio complete the cancellation

        except CapabilityDeniedError as e:
            logger.warning("Task %s blocked by capability policy: %s", task_id, e)
            duration = (time.time() - start_time) if "start_time" in locals() else 0
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.FAILED.value,
                    datetime.now().isoformat(),
                    duration,
                    str(e),
                    task_id,
                ),
            )
            await self._broadcast(task_id, "status", TaskStatus.FAILED.value)
            await self._invalidate_cached_views()
            await db.log_audit(
                "task_capability_denied",
                f"Task blocked by capability policy: {str(e)}",
                severity="warning",
                context={
                    "task_id": task_id,
                    "denied_capabilities": sorted(e.denied_capabilities),
                    "plugin_id": plugin_id,
                },
                task_id=task_id,
            )

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)

            # Update task as failed
            duration = (time.time() - start_time) if 'start_time' in locals() else 0
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.FAILED.value,
                    datetime.now().isoformat(),
                    duration,
                    str(e),
                    task_id
                )
            )

            await self._broadcast(task_id, "status", TaskStatus.FAILED.value)
            await self._invalidate_cached_views()

            await db.log_audit(
                "task_failed",
                f"Task failed: {str(e)}",
                severity="error",
                context={"task_id": task_id, "error": str(e)},
                task_id=task_id
            )
        finally:
            # Always clean up: remove from the in-memory registry and
            # release the concurrency slot regardless of how the task ended.
            self.running_tasks.pop(task_id, None)
            self._process_pids.pop(task_id, None)
            await concurrent_limiter.release(task_id)
    
    async def _execute_command(
        self,
        command: list,
        task_id: str,
        timeout: int = 600
    ) -> tuple:
        """
        Execute command in subprocess and stream output.

        Args:
            command: Command as list
            task_id: Task identifier for logging
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (output, exit_code)
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            self._process_pids[task_id] = process.pid

            output_lines = []

            async def read_stream():
                stdout = process.stdout
                if stdout is None:
                    return
                while not stdout.at_eof():
                    line = await stdout.readline()
                    if line:
                        decoded_line = line.decode("utf-8", errors="replace")
                        output_lines.append(decoded_line)
                        await self._broadcast(task_id, "output", decoded_line)

            try:
                await asyncio.wait_for(read_stream(), timeout=timeout)
                await process.wait()
                self._process_pids.pop(task_id, None)
                return "".join(output_lines), process.returncode if process.returncode is not None else -1

            except asyncio.TimeoutError:
                logger.warning(
                    "Task %s timed out after %ds — terminating process group (pid=%d)",
                    task_id, timeout, process.pid,
                )
                await _terminate_process_group(process.pid, task_id)
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except asyncio.TimeoutError:
                    pass
                self._process_pids.pop(task_id, None)
                return "".join(output_lines) + "\nTask timed out", -1

            except asyncio.CancelledError:
                logger.warning(
                    "Task %s cancelled — terminating process group (pid=%d)",
                    task_id, process.pid,
                )
                await _terminate_process_group(process.pid, task_id)
                try:
                    await asyncio.wait_for(process.wait(), timeout=3)
                except asyncio.TimeoutError:
                    pass
                self._process_pids.pop(task_id, None)
                raise

        except asyncio.CancelledError:
            self._process_pids.pop(task_id, None)
            raise
        except Exception as e:
            self._process_pids.pop(task_id, None)
            logger.error(f"Failed to execute command: {e}")
            return f"Execution error: {str(e)}", -1

    def _resolve_execution_timeout(self, inputs: Dict[str, Any]) -> int:
        """Resolve per-task process timeout from plugin inputs.

        The caller may request a shorter timeout than the operator cap, but
        never a longer one. ``settings.sandbox_timeout`` is the hard ceiling
        and is always enforced regardless of what the client supplies.
        """
        for key in ("max_scan_time", "timeout"):
            raw_value = inputs.get(key)
            try:
                timeout = int(raw_value)
            except (TypeError, ValueError):
                continue
            if timeout > 0:
                return min(timeout, settings.sandbox_timeout)
        return settings.sandbox_timeout

    def _classify_command_result(self, plugin, output: str, exit_code: int) -> tuple[str, Optional[str]]:
        """Map raw process exit codes into task status with plugin-specific tolerances."""
        normalized_output = output.lower()

        if "unknown option:" in normalized_output or "flag provided but not defined:" in normalized_output:
            return (
                TaskStatus.FAILED.value,
                output or "Tool rejected one or more generated CLI options. Check the final command and raw output for details.",
            )

        if exit_code == 0:
            return TaskStatus.COMPLETED.value, None

        output_config = plugin.output if isinstance(plugin.output, dict) else {}
        tolerated_exit_codes = output_config.get("nonfatal_exit_codes", [])
        success_patterns = output_config.get("success_output_patterns", [])

        try:
            tolerated = {int(code) for code in tolerated_exit_codes}
        except (TypeError, ValueError):
            tolerated = set()

        matched_success_pattern = any(
            isinstance(pattern, str) and pattern.lower() in normalized_output
            for pattern in success_patterns
        )

        if exit_code in tolerated and matched_success_pattern:
            logger.info(
                "Treating exit code %s from %s as completed due to matching success output",
                exit_code,
                plugin.id,
            )
            return TaskStatus.COMPLETED.value, None

        return (
            TaskStatus.FAILED.value,
            f"Tool returned non-zero exit code {exit_code}. Check raw output for details.",
        )

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully
        """
        if task_id not in self.running_tasks:
            return False
        task = self.running_tasks[task_id]

        pid = self._process_pids.get(task_id)
        if pid is not None:
            await _terminate_process_group(pid, task_id)

        task.cancel()

        # If docker is enabled, forcefully kill the sandbox container
        if settings.docker_enabled:
            try:
                killer = await asyncio.create_subprocess_exec(
                    "docker", "kill", f"secuscan_task_{task_id}",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                await killer.communicate()
            except Exception as e:
                logger.error(f"Failed to kill docker container for {task_id}: {e}")

        db = await get_db()
        await db.execute(
            "UPDATE tasks SET status = ?, completed_at = ? WHERE id = ?",
            (TaskStatus.CANCELLED.value, datetime.now().isoformat(), task_id)
        )

        await self._broadcast(task_id, "status", TaskStatus.CANCELLED.value)
        await self._invalidate_cached_views()

        await db.log_audit(
            "task_cancelled",
            "Task cancelled by user",
            task_id=task_id
        )

        return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get task status and progress"""
        db = await get_db()
        task_row = await db.fetchone(
            """
            SELECT id, plugin_id, tool_name, target, status, scan_phase, created_at, started_at, completed_at,
                   duration_seconds, exit_code, error_message, preset, inputs_json, execution_context_json
            FROM tasks WHERE id = ?
            """,
            (task_id,)
        )
        if not task_row:
            return None

        queue_position = None
        pending_count = None

        if task_row["status"] == TaskStatus.QUEUED.value:
            queued_rows = await db.fetchall(
                "SELECT id FROM tasks WHERE status = ? ORDER BY created_at ASC",
                (TaskStatus.QUEUED.value,)
            )
            ids = [r["id"] for r in queued_rows]
            pending_count = len(ids)
            queue_position = (ids.index(task_id) + 1) if task_id in ids else None

        return {
            "task_id": task_row["id"],
            "plugin_id": task_row["plugin_id"],
            "tool": task_row["tool_name"],
            "target": task_row["target"],
            "status": task_row["status"],
            "scan_phase": task_row.get("scan_phase"),
            "created_at": task_row["created_at"],
            "started_at": task_row["started_at"],
            "completed_at": task_row["completed_at"],
            "duration_seconds": task_row["duration_seconds"],
            "exit_code": task_row["exit_code"],
            "error_message": task_row["error_message"],
            "preset": task_row["preset"],
            "execution_context": normalize_execution_context(
                json.loads(_row_value(task_row, "execution_context_json", "{}") or "{}")
            ),
            "queue_position": queue_position,
            "pending_count": pending_count,
        }

    async def _hydrate_inputs_with_execution_context(
        self,
        *,
        db,
        owner_id: str,
        inputs: Dict[str, Any],
        execution_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add auth/session material derived from stored profiles."""
        effective_inputs = dict(inputs)
        target_policy = await get_target_policy(
            db,
            owner_id,
            execution_context.get("target_policy_id"),
        )
        if target_policy:
            effective_inputs["__target_policy"] = target_policy

        credential_profile = await get_credential_profile(
            db,
            owner_id,
            execution_context.get("credential_profile_id"),
        )
        if credential_profile:
            headers = credential_profile.get("extra_headers", {}) or {}
            effective_inputs["__extra_headers"] = {
                str(key): str(value) for key, value in headers.items()
            }
            username = await self._read_vault_secret(db, credential_profile.get("username_secret_name"))
            password = await self._read_vault_secret(db, credential_profile.get("password_secret_name"))
            if username is not None and password is not None:
                token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
                effective_inputs.setdefault("__extra_headers", {})
                effective_inputs["__extra_headers"]["Authorization"] = f"Basic {token}"

        session_profile = await get_session_profile(
            db,
            owner_id,
            execution_context.get("session_profile_id"),
        )
        if session_profile:
            extra_headers = session_profile.get("extra_headers", {}) or {}
            if extra_headers:
                effective_inputs.setdefault("__extra_headers", {})
                for key, value in extra_headers.items():
                    effective_inputs["__extra_headers"][str(key)] = str(value)
            cookie_secret = await self._read_vault_secret(db, session_profile.get("cookie_secret_name"))
            if cookie_secret:
                try:
                    parsed = json.loads(cookie_secret)
                    if isinstance(parsed, dict):
                        effective_inputs["__cookies"] = {
                            str(key): str(value) for key, value in parsed.items()
                        }
                except json.JSONDecodeError:
                    effective_inputs["__cookies"] = {"session": cookie_secret}

        effective_inputs["__execution_context"] = execution_context
        return effective_inputs

    async def _read_vault_secret(self, db, secret_name: Any) -> Optional[str]:
        if not secret_name:
            return None
        row = await db.fetchone(
            "SELECT encrypted_value FROM credential_vault WHERE name = ?",
            (str(secret_name),),
        )
        if not row:
            return None
        crypto = VaultCrypto(settings.resolved_vault_key)
        return crypto.decrypt(row["encrypted_value"])

    def _deserialize_finding_rows(self, rows: List[Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        json_fields = {
            "metadata_json": "metadata",
            "risk_factors_json": "risk_factors",
            "evidence_json": "evidence",
            "asset_refs_json": "asset_refs",
            "references_json": "references",
            "corroborating_sources_json": "corroborating_sources",
        }
        for row in rows:
            item = dict(row)
            for source_key, target_key in json_fields.items():
                value = item.pop(source_key, None)
                if isinstance(value, str):
                    try:
                        item[target_key] = json.loads(value)
                    except json.JSONDecodeError:
                        item[target_key] = value
                elif value is not None:
                    item[target_key] = value
            findings.append(item)
        return findings

    async def _load_previous_task_findings(
        self,
        db,
        *,
        owner_id: str,
        plugin_id: str,
        target: str,
        task_id: str,
    ) -> List[Dict[str, Any]]:
        previous_task = await db.fetchone(
            """
            SELECT id
            FROM tasks
            WHERE owner_id = ? AND plugin_id = ? AND target = ? AND id != ?
              AND status IN (?, ?)
            ORDER BY COALESCE(completed_at, created_at) DESC
            LIMIT 1
            """,
            (
                owner_id,
                plugin_id,
                target,
                task_id,
                TaskStatus.COMPLETED.value,
                TaskStatus.FAILED.value,
            ),
        )
        if not previous_task:
            return []

        rows = await db.fetchall(
            "SELECT * FROM findings WHERE owner_id = ? AND task_id = ? ORDER BY discovered_at DESC",
            (owner_id, previous_task["id"]),
        )
        return self._deserialize_finding_rows(rows)

    def _normalize_asset_service_record(self, target: str, service: Dict[str, Any]) -> Dict[str, Any]:
        metadata = service.get("metadata", {}) if isinstance(service.get("metadata"), dict) else {}
        host = str(service.get("host") or target)
        port = service.get("port")
        protocol = service.get("protocol")
        cert_san = service.get("cert_san") or service.get("cert_sans") or metadata.get("cert_san") or metadata.get("cert_sans") or []
        if not isinstance(cert_san, list):
            cert_san = [cert_san]
        fingerprint = service.get("service_fingerprint")
        if not fingerprint:
            fingerprint = " ".join(
                str(part).strip()
                for part in (
                    service.get("product"),
                    service.get("version"),
                    service.get("service"),
                    service.get("title"),
                )
                if str(part or "").strip()
            ) or None
        return {
            **service,
            "host": host,
            "target": target,
            "asset_id": str(service.get("asset_id") or _stable_asset_id(target, host, port, protocol)),
            "cert_san": cert_san,
            "metadata": metadata,
            "service_fingerprint": fingerprint,
        }

    def _build_severity_counts(self, findings: List[Dict[str, Any]]) -> Dict[str, int]:
        severity_counts: Dict[str, int] = {}
        for finding in findings:
            severity = str(finding.get("severity", "info")).lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        return severity_counts

    async def _build_result_contract(
        self,
        db,
        *,
        task_id: str,
        owner_id: str,
        plugin_id: str,
        target: str,
        result: Dict[str, Any],
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        normalized_findings = await normalize_and_correlate_findings(
            db,
            owner_id=owner_id,
            plugin_id=plugin_id,
            target=target,
            findings=[item for item in result.get("findings", []) if isinstance(item, dict)],
        )
        previous_findings = await self._load_previous_task_findings(
            db,
            owner_id=owner_id,
            plugin_id=plugin_id,
            target=target,
            task_id=task_id,
        )
        asset_services = [
            self._normalize_asset_service_record(target, item)
            for item in (result.get("asset_services") or result.get("services") or [])
            if isinstance(item, dict)
        ]
        structured_result = dict(result)
        structured_result["findings"] = normalized_findings
        structured_result["asset_services"] = asset_services
        structured_result["services"] = asset_services
        structured_result["finding_groups"] = build_finding_groups(normalized_findings)
        structured_result["asset_summary"] = build_asset_summary(normalized_findings, asset_services)
        structured_result["scan_diff"] = build_scan_diff(normalized_findings, previous_findings)
        structured_result["severity_counts"] = self._build_severity_counts(normalized_findings)
        structured_result["count"] = len(normalized_findings)
        return structured_result, previous_findings, asset_services

    async def _persist_finding(
        self,
        db,
        *,
        owner_id: str,
        task_id: str,
        plugin_id: str,
        target: str,
        finding: Dict[str, Any],
    ) -> Dict[str, Any]:
        u_id = str(uuid.uuid4()).replace("-", "")
        finding_id = f"finding:{task_id}:{u_id[:8]}"

        _validate_risk_fields(finding)
        exploitability = finding.get("exploitability")
        confidence = finding.get("confidence")
        asset_exposure = finding.get("asset_exposure")
        discovered = _parse_discovered_at(finding)
        target_value = str(finding.get("target") or target)
        metadata = finding.get("metadata", {}) if isinstance(finding.get("metadata"), dict) else {}
        evidence = finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else []
        asset_refs = finding.get("asset_refs", []) if isinstance(finding.get("asset_refs"), list) else []
        references = finding.get("references", []) if isinstance(finding.get("references"), list) else []
        corroborating_sources = finding.get("corroborating_sources", []) if isinstance(finding.get("corroborating_sources"), list) else []
        first_seen_at = str(finding.get("first_seen_at") or discovered.isoformat())
        last_seen_at = str(finding.get("last_seen_at") or discovered.isoformat())
        occurrence_count = int(finding.get("occurrence_count") or 1)
        evidence_count = int(finding.get("evidence_count") or len(evidence))
        risk_score = compute_risk_score(
            severity=finding["severity"],
            exploitability=exploitability,
            asset_exposure=asset_exposure,
            discovered_at=discovered,
            confidence=confidence,
        )
        risk_factors = compute_risk_factors(
            severity=finding["severity"],
            exploitability=exploitability,
            asset_exposure=asset_exposure,
            discovered_at=discovered,
            confidence=confidence,
            risk_score=risk_score,
        )

        await db.execute(
            """
            INSERT INTO findings (
                id, owner_id, task_id, plugin_id, title, category, severity,
                target, description, remediation, proof, cvss, cve,
                metadata_json, discovered_at,
                exploitability, confidence, validated, validation_method,
                confidence_reason, finding_kind, finding_group_id, asset_id,
                first_seen_at, last_seen_at, occurrence_count, corroborating_sources_json,
                evidence_count, analyst_status, retest_status, evidence_json, asset_refs_json,
                service_fingerprint, cpe, references_json,
                asset_exposure, risk_score, risk_factors_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                finding_id,
                owner_id,
                task_id,
                plugin_id,
                finding["title"],
                finding["category"],
                finding["severity"],
                target_value,
                finding["description"],
                finding.get("remediation", ""),
                finding.get("proof"),
                finding.get("cvss"),
                finding.get("cve"),
                json.dumps(metadata),
                discovered.isoformat(),
                exploitability,
                confidence,
                1 if finding.get("validated") else 0,
                finding.get("validation_method"),
                finding.get("confidence_reason"),
                str(finding.get("finding_kind") or "observation"),
                finding.get("finding_group_id"),
                finding.get("asset_id"),
                first_seen_at,
                last_seen_at,
                occurrence_count,
                json.dumps(corroborating_sources),
                evidence_count,
                str(finding.get("analyst_status") or "new"),
                str(finding.get("retest_status") or "not_requested"),
                json.dumps(evidence),
                json.dumps(asset_refs),
                finding.get("service_fingerprint"),
                finding.get("cpe"),
                json.dumps(references),
                asset_exposure,
                risk_score,
                json.dumps(risk_factors),
            ),
        )
        return {
            **finding,
            "id": finding_id,
            "plugin_id": plugin_id,
            "target": target_value,
            "discovered_at": discovered.isoformat(),
            "metadata": metadata,
            "evidence": evidence,
            "asset_refs": asset_refs,
            "references": references,
            "corroborating_sources": corroborating_sources,
            "first_seen_at": first_seen_at,
            "last_seen_at": last_seen_at,
            "occurrence_count": occurrence_count,
            "evidence_count": evidence_count,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
        }

    async def _upsert_findings_and_report(self, db, task_id: str, owner_id: str, plugin, plugin_id: str, target: str, status: str, output: str = ""):
        """Persist derived findings and report records into SQLite."""
        parsed = self._parse_results(plugin, output)
        structured_result, previous_findings, asset_services = await self._build_result_contract(
            db,
            task_id=task_id,
            owner_id=owner_id,
            plugin_id=plugin_id,
            target=target,
            result=parsed,
        )
        findings_data: List[Dict[str, Any]] = []
        for finding in structured_result.get("findings", []):
            findings_data.append(
                await self._persist_finding(
                    db,
                    owner_id=owner_id,
                    task_id=task_id,
                    plugin_id=plugin_id,
                    target=target,
                    finding=finding,
                )
            )

        structured_result["findings"] = findings_data
        structured_result["severity_counts"] = self._build_severity_counts(findings_data)
        structured_result["finding_groups"] = build_finding_groups(findings_data)
        structured_result["asset_summary"] = build_asset_summary(findings_data, asset_services)
        structured_result["scan_diff"] = build_scan_diff(findings_data, previous_findings)

        await db.execute(
            "UPDATE tasks SET structured_json = ? WHERE id = ?",
            (json.dumps(structured_result), task_id)
        )

        await db.execute(
            """
            INSERT INTO reports (
                id, owner_id, task_id, name, type, generated_at, status, findings, pages
            ) VALUES (?, ?, ?, ?, ?, (datetime('now')), ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                findings = EXCLUDED.findings,
                pages = EXCLUDED.pages
            """,
            (
                f"report:{task_id}",
                owner_id,
                task_id,
                f"{plugin.name} Report",
                "technical",
                "ready" if status == TaskStatus.COMPLETED.value else "failed",
                len(findings_data),
                1,
            ),
        )

        await self._persist_result_resources(
            db,
            owner_id=owner_id,
            task_id=task_id,
            plugin_id=plugin_id,
            target=target,
            result=structured_result,
        )

    async def _upsert_findings_and_report_from_scanner(self, db, task_id: str, owner_id: str, scanner: Any, plugin_id: str, target: str, status: str, result: Dict[str, Any]):
        """Persist modular scanner results into findings, and reports."""
        structured_result, previous_findings, asset_services = await self._build_result_contract(
            db,
            task_id=task_id,
            owner_id=owner_id,
            plugin_id=plugin_id,
            target=target,
            result=result,
        )
        findings_data: List[Dict[str, Any]] = []
        for finding in structured_result.get("findings", []):
            findings_data.append(
                await self._persist_finding(
                    db,
                    owner_id=owner_id,
                    task_id=task_id,
                    plugin_id=plugin_id,
                    target=target,
                    finding=finding,
                )
            )

        structured_result["findings"] = findings_data
        structured_result["severity_counts"] = self._build_severity_counts(findings_data)
        structured_result["finding_groups"] = build_finding_groups(findings_data)
        structured_result["asset_summary"] = build_asset_summary(findings_data, asset_services)
        structured_result["scan_diff"] = build_scan_diff(findings_data, previous_findings)

        await db.execute(
            "UPDATE tasks SET structured_json = ? WHERE id = ?",
            (json.dumps(structured_result), task_id)
        )

        # Create/Update report
        await db.execute(
            """
            INSERT INTO reports (
                id, owner_id, task_id, name, type, generated_at, status, findings, pages
            ) VALUES (?, ?, ?, ?, ?, (datetime('now')), ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                findings = EXCLUDED.findings,
                pages = EXCLUDED.pages
            """,
            (
                f"report:{task_id}",
                owner_id,
                task_id,
                f"{scanner.name} Report",
                "professional" if status == TaskStatus.COMPLETED.value else "failed",
                "ready" if status == TaskStatus.COMPLETED.value else "failed",
                len(findings_data),
                2, # Professional reports are typically multi-page
            ),
        )

        await self._persist_result_resources(
            db,
            owner_id=owner_id,
            task_id=task_id,
            plugin_id=plugin_id,
            target=target,
            result=structured_result,
        )

    async def _persist_result_resources(
        self,
        db,
        *,
        owner_id: str,
        task_id: str,
        plugin_id: str,
        target: str,
        result: Dict[str, Any],
    ) -> None:
        crawl = result.get("crawl")
        if isinstance(crawl, dict) and crawl:
            await persist_crawl_run(
                db,
                owner_id=owner_id,
                task_id=task_id,
                plugin_id=plugin_id,
                target=target,
                crawl=crawl,
            )

        asset_services = result.get("asset_services") or result.get("services")
        if isinstance(asset_services, list) and asset_services:
            await replace_asset_services(
                db,
                owner_id=owner_id,
                task_id=task_id,
                plugin_id=plugin_id,
                target=target,
                services=[item for item in asset_services if isinstance(item, dict)],
            )

    def _parse_results(self, plugin, output: str) -> Dict[str, Any]:
        """Route to appropriate parser based on plugin metadata."""
        parser_type = plugin.output.get("parser")
        parser_input = self._resolve_parser_input(plugin, output)
        
        # 1. Check for custom parser.py in plugin directory (Recommended)
        plugin_manager = get_plugin_manager()
        plugin_dir = plugin_manager.plugins_dir / plugin.id
        parser_path = plugin_dir / "parser.py"
        
        if parser_path.exists():
            if not plugin_manager.verify_parser_at_exec_time(plugin, plugin_dir):
                raise ValueError(
                    f"Security error: parser.py integrity check failed for plugin {plugin.id!r}; "
                    "the file may have been tampered with. Rotate the plugin checksum or "
                    "reinstall the plugin before retrying."
                )
            try:
                parsed = run_parser_in_sandbox(
                    parser_path=parser_path,
                    plugin_id=plugin.id,
                    parser_input=parser_input,
                    timeout_seconds=settings.parser_sandbox_timeout_seconds,
                    max_output_bytes=settings.parser_sandbox_max_output_bytes,
                )
                return self._normalize_parsed_result(plugin, parser_input, parsed)
            except ParserSandboxError as exc:
                logger.error("Parser sandbox error for plugin '%s': %s", plugin.id, exc)
                # For plugins that declared a custom parser, sandbox failure is a hard
                # error — do NOT fall through to built-in parsers, which would produce
                # empty or misleading results unrelated to the custom parser's logic.
                raise RuntimeError(
                    f"Custom parser failed for plugin '{plugin.id}': {exc.reason}"
                ) from exc
            except Exception as exc:
                logger.error("Unexpected error running parser sandbox for '%s': %s", plugin.id, exc)
                raise RuntimeError(
                    f"Custom parser encountered an unexpected error for plugin '{plugin.id}': {exc}"
                ) from exc

        # 2. Fallback to legacy built-in parsers (only reached when no parser.py exists)
        if parser_type == "builtin_nmap":
            return self._normalize_parsed_result(plugin, parser_input, self._parse_nmap_output(parser_input))
        elif parser_type == "builtin_http":
            return self._normalize_parsed_result(plugin, parser_input, self._parse_http_output(parser_input))
        
        return self._normalize_parsed_result(plugin, parser_input, {"findings": [], "raw": parser_input})

    def _resolve_parser_input(self, plugin, output: str) -> str:
        """Prefer report-file content when configured, fallback to command output."""
        report_path = plugin.output.get("report_path")
        if isinstance(report_path, str) and report_path.strip():
            path = Path(report_path)
            if path.exists() and path.is_file():
                try:
                    logger.info("Using parser report file for %s: %s", plugin.id, path)
                    return path.read_text(encoding="utf-8", errors="replace")
                except Exception as exc:
                    logger.warning("Failed to read parser report file %s: %s", path, exc)

        return output

    def _normalize_parsed_result(self, plugin, parser_input: str, parsed: Any) -> Dict[str, Any]:
        """
        Normalize parser output shape so downstream report/asset logic always receives:
        { findings: List[Finding], ... }.
        """
        normalized: Dict[str, Any]
        raw_findings: Any

        if isinstance(parsed, dict):
            normalized = dict(parsed)
            raw_findings = normalized.get("findings", [])
        elif isinstance(parsed, list):
            normalized = {}
            raw_findings = parsed
        else:
            normalized = {}
            raw_findings = []

        if isinstance(raw_findings, dict):
            raw_findings = [raw_findings]
        if not isinstance(raw_findings, list):
            raw_findings = []

        findings = [
            self._normalize_finding(plugin, item)
            for item in raw_findings
            if isinstance(item, dict)
        ]

        # Fallback for JSON/JSONL plugin outputs where parser returns empty or unexpected data.
        if not findings and str(plugin.output.get("format", "")).lower() in {"json", "jsonl"}:
            findings = self._parse_json_fallback_findings(plugin, parser_input)

        normalized["findings"] = findings
        if "count" not in normalized:
            normalized["count"] = len(findings)
        if "raw" not in normalized and not findings:
            normalized["raw"] = parser_input
        return normalized

    def _normalize_finding(self, plugin, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure finding has all required keys and normalized severity."""
        severity = str(finding.get("severity", "info")).lower()
        severity_map = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "moderate": "medium",
            "warning": "medium",
            "warn": "medium",
            "low": "low",
            "info": "info",
            "informational": "info",
            "error": "high",
        }
        normalized_severity = severity_map.get(severity, "info")

        category = finding.get("category") or finding.get("type") or str(plugin.category).title()
        title = finding.get("title") or finding.get("name") or "Security Finding"
        description = finding.get("description") or finding.get("message") or str(title)

        metadata = finding.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {"value": metadata}

        return {
            "title": str(title),
            "category": str(category),
            "severity": normalized_severity,
            "description": str(description),
            "remediation": str(finding.get("remediation", "")),
            "proof": finding.get("proof"),
            "cvss": finding.get("cvss"),
            "cve": finding.get("cve"),
            "metadata": metadata,
            "exploitability": finding.get("exploitability"),
            "confidence": finding.get("confidence"),
            "validated": bool(finding.get("validated", False)),
            "validation_method": finding.get("validation_method"),
            "confidence_reason": finding.get("confidence_reason"),
            "evidence": finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else [],
            "asset_refs": finding.get("asset_refs", []) if isinstance(finding.get("asset_refs"), list) else [],
            "service_fingerprint": finding.get("service_fingerprint"),
            "cpe": finding.get("cpe"),
            "references": finding.get("references", []) if isinstance(finding.get("references"), list) else [],
            "asset_exposure": finding.get("asset_exposure"),
        }

    def _parse_json_fallback_findings(self, plugin, parser_input: str) -> List[Dict[str, Any]]:
        """Best-effort conversion of JSON payloads into finding entries."""
        try:
            data = json.loads(parser_input)
        except Exception:
            return []

        findings: List[Dict[str, Any]] = []

        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                if isinstance(item, dict):
                    findings.append(self._json_item_to_finding(plugin, item, f"Item {idx}"))
                else:
                    findings.append(
                        self._normalize_finding(
                            plugin,
                            {
                                "title": f"{plugin.name} Result #{idx}",
                                "category": plugin.category,
                                "severity": "info",
                                "description": str(item),
                            },
                        )
                    )
            return findings

        if isinstance(data, dict):
            # Common scanner shape: { "results": [...] }
            for list_key in ("results", "findings", "issues", "vulnerabilities"):
                if isinstance(data.get(list_key), list):
                    for idx, item in enumerate(data[list_key], start=1):
                        if isinstance(item, dict):
                            findings.append(self._json_item_to_finding(plugin, item, f"{list_key} #{idx}"))
                    if findings:
                        return findings

            findings.append(self._json_item_to_finding(plugin, data, plugin.name))

        return findings

    def _json_item_to_finding(self, plugin, item: Dict[str, Any], default_title: str) -> Dict[str, Any]:
        title = (
            item.get("title")
            or item.get("name")
            or item.get("issue")
            or item.get("message")
            or default_title
        )
        description = item.get("description") or item.get("detail") or item.get("message") or str(item)
        severity = item.get("severity", "info")
        category = item.get("category", str(plugin.category).title())
        return self._normalize_finding(
            plugin,
            {
                "title": title,
                "category": category,
                "severity": severity,
                "description": description,
                "metadata": item,
            },
        )

    def _parse_nmap_output(self, output: str) -> Dict[str, Any]:
        """Simple regex-based nmap output parser."""
        findings = []
        ports = []
        services = []
        
        # Regex for open ports: 80/tcp open http
        port_pattern = re.compile(r"(\d+)/(tcp|udp)\s+open\s+([\w-]+)")
        for match in port_pattern.finditer(output):
            port_str, proto, service = match.groups()
            port_val = int(port_str)
            ports.append(port_val)
            services.append(service)
            findings.append({
                "title": f"Open Port: {port_str}/{proto} ({service})",
                "category": "Network Service",
                "severity": "low",
                "description": f"Port {port_str} is open and running {service} service.",
                "remediation": "Close unnecessary ports and use a firewall to restrict access.",
                "metadata": {"port": port_str, "protocol": proto, "service": service}
            })
        
        return {
            "open_ports": sorted(list(set(ports))),
            "services": sorted(list(set(services))),
            "findings": findings
        }

    def _parse_http_output(self, output: str) -> Dict[str, Any]:
        """Simple regex-based curl/http output parser."""
        findings = []
        techs = []

        if server_match := re.search(r"(?i)Server:\s*(.+)", output):
            server = server_match[1].strip()
            techs.append(server)
            findings.append({
                "title": f"Web Server Disclosed: {server}",
                "category": "Information Disclosure",
                "severity": "low",
                "description": f"The web server discloses its version: {server}",
                "remediation": "Disable the Server header in web server configuration.",
                "metadata": {"server": server}
            })

        if powered_match := re.search(r"(?i)X-Powered-By:\s*(.+)", output):
            powered = powered_match[1].strip()
            techs.append(powered)
            findings.append({
                "title": f"X-Powered-By Disclosed: {powered}",
                "category": "Information Disclosure",
                "severity": "low",
                "description": f"The application discloses its technology stack: {powered}",
                "remediation": "Disable the X-Powered-By header.",
                "metadata": {"tech": powered}
            })

        return {
            "technologies": sorted(list(set(techs))),
            "findings": findings
        }

    async def _dispatch_task_notifications(self, db, task_id: str) -> None:
        """Evaluate notification rules for all findings on a completed task."""
        try:
            results = await process_task_notifications(db, task_id)
            sent = sum(
                1
                for r in results
                if not r.skipped and r.status == NotificationDeliveryStatus.SUCCESS
            )
            if sent:
                logger.info("Task %s: delivered %d notification(s)", task_id, sent)
        except Exception as exc:
            logger.warning(
                "Task %s: notification dispatch failed: %s",
                task_id,
                exc,
                exc_info=True,
            )

    async def _invalidate_cached_views(self):
        """Clear cached aggregate views after write operations."""
        try:
            cache_client = await get_cache()
            await cache_client.delete_prefix("summary:")
            await cache_client.delete_prefix("assets:")
            await cache_client.delete_prefix("findings:")
            await cache_client.delete_prefix("surface:")
            await cache_client.delete_prefix("reports:")
            await cache_client.delete_prefix("tasks:")
        except Exception as exc:
            logger.warning("Cache invalidation skipped: %s", exc)


# Global executor instance
executor = TaskExecutor()
