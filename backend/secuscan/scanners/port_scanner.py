import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from .base import BaseScanner
from ..plugins import get_plugin_manager


class PortScanner(BaseScanner):
    """
    Orchestrates Nmap scanning with refined result parsing.
    Equivalent to Pentest-Tools 'Port Scanner'.
    """

    @property
    def name(self) -> str:
        return "Port Scanner"

    @property
    def category(self) -> str:
        return "Network Security"

    # ------------------------------------------------------------------
    # Input normalisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_scan_type(raw: Any) -> str:
        """Map caller-supplied scan_type to the nmap plugin's SELECT value.

        The plugin field 'scan_type' accepts only "S" | "T" | "U".
        Callers may pass the raw letter, "-sX", or "sX" forms.
        Raises ValueError for any value that cannot be resolved.
        """
        _VALID = {"S", "T", "U"}
        if not raw:
            return "T"
        value = str(raw).strip().upper()
        # Already a bare valid letter
        if value in _VALID:
            return value
        # Strip a leading "-s" or "s" prefix (e.g. "-sT" → "T", "sS" → "S")
        # The result must be exactly one valid letter — multi-char leftovers are invalid.
        stripped = re.sub(r"^-?S", "", value)
        if len(stripped) == 1 and stripped in _VALID:
            return stripped
        raise ValueError(
            f"Invalid scan_type {raw!r}: must be one of 'S' (SYN), 'T' (TCP connect), 'U' (UDP)"
        )

    @staticmethod
    def _resolve_ports(raw: Any) -> str:
        """Map shorthand port specs to a clean numeric range string accepted by the plugin.

        Returns:
            Empty string  → use plugin default (top-100 via command template)
            Numeric range → passed through as-is
        """
        if not raw or raw in ("", "top100"):
            return ""
        if raw == "top1000":
            return "1-1000"
        if raw == "all":
            return "1-65535"
        # Validate strict port spec: comma-separated port numbers/ranges
        if re.match(r"^\d+(-\d+)?(,\d+(-\d+)?)*$", str(raw)):
            return str(raw)
        raise ValueError(
            f"Invalid port specification {raw!r}: use a number (80), range (1-1000), "
            "or comma-separated list (22,80,443), or a shorthand: top100, top1000, all"
        )

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Runs Nmap scan and parses output into structured findings."""
        self.update_progress(0.1)

        plugin_inputs = {
            "target": target,
            "scan_type": self._resolve_scan_type(inputs.get("scan_type", "T")),
            "ports": self._resolve_ports(inputs.get("ports", "")),
            "service_detection": bool(inputs.get("service_detection", True)),
            "os_detection": bool(inputs.get("os_detection", False)),
            "safe_mode": bool(inputs.get("safe_mode", True)),
        }

        plugin_manager = get_plugin_manager()
        command = plugin_manager.build_command("nmap", plugin_inputs)

        if not command:
            raise ValueError("Failed to build nmap command")

        self.update_progress(0.2)
        output, exit_code = await self._execute_command(command)
        self.update_progress(0.8)

        findings = self._parse_nmap_output(output, target)

        self.update_progress(1.0)
        return {
            "findings": findings,
            "summary": [
                f"Scanned {target} for open ports.",
                f"Discovered {len(findings)} open ports.",
            ],
            "open_ports": [f["metadata"]["port"] for f in findings],
            "status": "completed" if exit_code == 0 else "failed",
        }

    async def _execute_command(self, command: List[str]) -> tuple:
        """Executes the command and returns (output, exit_code)"""
        import asyncio.subprocess
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await process.communicate()
            return stdout.decode("utf-8", errors="replace"), process.returncode
        except asyncio.CancelledError:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise

    def _parse_nmap_output(self, output: str, target: str) -> List[Dict[str, Any]]:
        findings = []
        port_pattern = re.compile(r"(\d+)/(tcp|udp)\s+open\s+([\w-]+)\s*(.*)")

        for match in port_pattern.finditer(output):
            port_str, proto, service, version = match.groups()

            title = f"Open Port: {port_str}/{proto} ({service})"
            description = f"Port {port_str} is open and running {service} service."
            if version.strip():
                description += f" Version detected: {version.strip()}"

            findings.append(
                {
                    "title": title,
                    "category": "Network Service",
                    "severity": self.normalize_severity("low"),
                    "target": target,
                    "description": description,
                    "remediation": "Close unnecessary ports and use a firewall to restrict access.",
                    "metadata": {
                        "port": port_str,
                        "protocol": proto,
                        "service": service,
                        "version": version.strip(),
                    },
                }
            )

        return findings
