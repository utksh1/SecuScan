"""
Task execution engine with Docker sandboxing
"""

import asyncio
from asyncio import subprocess
import uuid
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
import re

from .cache import get_cache
from .config import settings
from .database import get_db
from .plugins import get_plugin_manager
from .models import TaskStatus

logger = logging.getLogger(__name__)


def extract_target(inputs: Dict[str, Any]) -> str:
    """Best-effort target extraction across plugin shapes."""
    return (
        inputs.get("target")
        or inputs.get("url")
        or inputs.get("host")
        or inputs.get("domain")
        or ""
    )


class TaskExecutor:
    """Executes security scanning tasks in isolated environments"""

    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # PubSub: Map of task_id to list of active async queues listening for output/status updates
        self._listeners: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, task_id: str) -> asyncio.Queue:
        """Subscribe to a task's real-time events."""
        if task_id not in self._listeners:
            self._listeners[task_id] = []
        q = asyncio.Queue()
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
            for q in self._listeners[task_id]:
                await q.put(event)
    
    async def create_task(
        self,
        plugin_id: str,
        inputs: Dict[str, Any],
        preset: Optional[str] = None,
        consent_granted: bool = False
    ) -> str:
        """
        Create a new scan task.
        
        Args:
            plugin_id: Plugin identifier
            inputs: User input values
            preset: Optional preset name
            consent_granted: Whether user granted consent
        
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
                id, plugin_id, tool_name, target, inputs_json, preset,
                status, consent_granted, safe_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                plugin_id,
                plugin.name,
                extract_target(inputs),
                json.dumps(inputs),
                preset,
                TaskStatus.QUEUED.value,
                consent_granted,
                inputs.get("safe_mode", True)
            )
        )
        
        # Log audit event
        await db.log_audit(
            "task_created",
            f"Task created for {plugin.name}",
            context={"task_id": task_id, "plugin_id": plugin_id, "target": inputs.get("target")},
            task_id=task_id,
            plugin_id=plugin_id
        )
        
        return task_id
    
    async def execute_task(self, task_id: str):
        """
        Execute a task asynchronously.
        
        Args:
            task_id: Task identifier
        """
        db = await get_db()

        try:
            # Update status to running
            await db.execute(
                "UPDATE tasks SET status = ?, started_at = ? WHERE id = ?",
                (TaskStatus.RUNNING.value, datetime.now().isoformat(), task_id)
            )

            # Get task details
            task_row = await db.fetchone(
                "SELECT plugin_id, inputs_json, safe_mode FROM tasks WHERE id = ?",
                (task_id,)
            )

            if not task_row:
                raise ValueError(f"Task not found: {task_id}")

            plugin_id = task_row["plugin_id"]
            inputs = json.loads(task_row["inputs_json"])
            safe_mode = bool(task_row["safe_mode"])
            target = extract_target(inputs)

            # Build command
            plugin_manager = get_plugin_manager()
            plugin = plugin_manager.get_plugin(plugin_id)
            if not plugin:
                raise ValueError(f"Plugin not found: {plugin_id}")
            
            command = plugin_manager.build_command(plugin_id, inputs)

            if not command:
                raise ValueError("Failed to build command")

            # Apply Docker Sandboxing if enabled
            if settings.docker_enabled:
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
                    docker_image,
                ]
                command = docker_cmd + command

            logger.info(f"Executing task {task_id}: {' '.join(command)}")
            await self._broadcast(task_id, "status", TaskStatus.RUNNING.value)

            # Execute command
            start_time = time.time()
            output, exit_code = await self._execute_command(command, task_id)
            duration = time.time() - start_time

            # Save raw output
            raw_path = Path(settings.raw_output_dir) / f"{task_id}.txt"
            with open(raw_path, 'w') as f:
                f.write(output)

            # Update task with results
            final_status = TaskStatus.COMPLETED.value if exit_code == 0 else TaskStatus.FAILED.value
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    duration_seconds = ?,
                    exit_code = ?,
                    raw_output_path = ?,
                    command_used = ?
                WHERE id = ?
                """,
                (
                    final_status,
                    datetime.now().isoformat(),
                    duration,
                    exit_code,
                    str(raw_path),
                    " ".join(command),
                    task_id
                )
            )

            await self._upsert_asset_and_report(
                db=db,
                task_id=task_id,
                plugin=plugin,
                plugin_id=plugin_id,
                target=target,
                status=final_status,
                output=output
            )

            await self._broadcast(task_id, "status", final_status)
            await self._invalidate_cached_views()

            # Log completion
            await db.log_audit(
                "task_completed",
                f"Task completed in {duration:.2f}s",
                context={"task_id": task_id, "exit_code": exit_code},
                task_id=task_id,
                plugin_id=plugin_id
            )

            logger.info(f"Task {task_id} completed in {duration:.2f}s")

        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")

            # Update task as failed
            await db.execute(
                """
                UPDATE tasks SET
                    status = ?,
                    completed_at = ?,
                    error_message = ?
                WHERE id = ?
                """,
                (
                    TaskStatus.FAILED.value,
                    datetime.now().isoformat(),
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
                stderr=subprocess.STDOUT
            )

            output_lines = []

            async def read_stream():
                stdout = process.stdout
                if stdout is None:
                    return
                    
                while not stdout.at_eof():
                    line = await stdout.readline()
                    if line:
                        decoded_line = line.decode('utf-8', errors='replace')
                        output_lines.append(decoded_line)
                        await self._broadcast(task_id, "output", decoded_line)

            try:
                await asyncio.wait_for(read_stream(), timeout=timeout)
                await process.wait()
                return "".join(output_lines), process.returncode if process.returncode is not None else -1

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return "".join(output_lines) + "\nTask timed out", -1

        except Exception as e:
            logger.error(f"Failed to execute command: {e}")
            return f"Execution error: {str(e)}", -1
    
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
            SELECT id, plugin_id, tool_name, target, status,
                   created_at, started_at, completed_at, duration_seconds,
                   inputs_json, preset
            FROM tasks WHERE id = ?
            """,
            (task_id,)
        )
        
        if not task_row:
            return None
        
        return {
            "task_id": task_row["id"],
            "plugin_id": task_row["plugin_id"],
            "tool": task_row["tool_name"],
            "target": task_row["target"],
            "status": task_row["status"],
            "created_at": task_row["created_at"],
            "started_at": task_row["started_at"],
            "completed_at": task_row["completed_at"],
            "duration_seconds": task_row["duration_seconds"],
            "inputs": json.loads(task_row["inputs_json"]) if task_row["inputs_json"] else {},
            "preset": task_row["preset"]
        }

    async def _upsert_asset_and_report(self, db, task_id: str, plugin, plugin_id: str, target: str, status: str, output: str = ""):
        """Persist derived asset, attack surface, and report records into SQLite."""
        parsed = self._parse_results(plugin, output)
        findings_data = parsed.get("findings", [])
        
        # Update task with structured results
        await db.execute(
            "UPDATE tasks SET structured_json = ? WHERE id = ?",
            (json.dumps(parsed), task_id)
        )

        if target:
            asset_id = f"asset:{target}"
            asset_type = "domain" if "." in target and ":" not in target else "service"
            risk_level = "medium" if plugin.safety.get("level") == "intrusive" else "low"
            if any(f["severity"] in ["critical", "high"] for f in findings_data):
                risk_level = "high"

            await db.execute(
                """
                INSERT INTO assets (
                    id, target, type, description, risk_level, status, last_scanned, 
                    scan_count, updated_at, open_ports, technologies, services
                ) VALUES (?, ?, ?, ?, ?, ?, (datetime('now')), 1, (datetime('now')), ?, ?, ?)
                ON CONFLICT (target) DO UPDATE SET
                    type = EXCLUDED.type,
                    description = EXCLUDED.description,
                    risk_level = EXCLUDED.risk_level,
                    status = EXCLUDED.status,
                    last_scanned = (datetime('now')),
                    scan_count = assets.scan_count + 1,
                    updated_at = (datetime('now')),
                    open_ports = EXCLUDED.open_ports,
                    technologies = EXCLUDED.technologies,
                    services = EXCLUDED.services
                """,
                (
                    asset_id,
                    target,
                    asset_type,
                    f"Observed by {plugin.name}",
                    risk_level,
                    "active",
                    json.dumps(parsed.get("open_ports", [])),
                    json.dumps(parsed.get("technologies", [])),
                    json.dumps(parsed.get("services", [])),
                ),
            )

            # Insert findings
            for finding in findings_data:
                # Use string splicing for compatibility
                u_id = str(uuid.uuid4()).replace("-", "")
                finding_id = f"finding:{task_id}:{u_id[:8]}"
                await db.execute(
                    """
                    INSERT INTO findings (
                        id, task_id, plugin_id, title, category, severity,
                        target, description, remediation, metadata_json, discovered_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, (datetime('now')))
                    """,
                    (
                        finding_id,
                        task_id,
                        plugin_id,
                        finding["title"],
                        finding["category"],
                        finding["severity"],
                        target,
                        finding["description"],
                        finding.get("remediation", ""),
                        json.dumps(finding.get("metadata", {})),
                    )
                )

            await db.execute(
                """
                INSERT INTO attack_surface_entries (
                    id, asset_id, category, item, details, risk, source, last_seen
                ) VALUES (?, ?, ?, ?, ?, ?, ?, (datetime('now')))
                ON CONFLICT (id) DO UPDATE SET
                    details = EXCLUDED.details,
                    risk = EXCLUDED.risk,
                    source = EXCLUDED.source,
                    last_seen = (datetime('now'))
                """,
                (
                    f"surface:{task_id}",
                    asset_id,
                    "Scanned Targets",
                    target,
                    f"{plugin.name} executed with status {status}. Found {len(findings_data)} findings.",
                    "medium" if any(f["severity"] in ["critical", "high"] for f in findings_data) else "info",
                    plugin.name,
                ),
            )

        await db.execute(
            """
            INSERT INTO reports (
                id, task_id, name, type, generated_at, status, findings, assets, pages
            ) VALUES (?, ?, ?, ?, (datetime('now')), ?, ?, ?, ?)
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                findings = EXCLUDED.findings,
                assets = EXCLUDED.assets,
                pages = EXCLUDED.pages
            """,
            (
                f"report:{task_id}",
                task_id,
                f"{plugin.name} Report",
                "technical",
                "ready" if status == TaskStatus.COMPLETED.value else "failed",
                len(findings_data),
                1 if target else 0,
                1,
            ),
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
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location(f"parser_{plugin.id}", parser_path)
                if spec is not None:
                    loader = spec.loader
                    if loader is not None:
                        module = importlib.util.module_from_spec(spec)
                        loader.exec_module(module)
                        if hasattr(module, "parse"):
                            logger.info(f"Using custom parser for {plugin.id}")
                            parsed = module.parse(parser_input)
                            return self._normalize_parsed_result(plugin, parser_input, parsed)
                        else:
                            logger.warning(f"Custom parser {parser_path} missing 'parse' function")
            except Exception as e:
                logger.error(f"Error executing custom parser for {plugin.id}: {e}")

        # 2. Fallback to legacy built-in parsers
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
            "metadata": metadata,
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
