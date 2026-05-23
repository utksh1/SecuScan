import asyncio
import json
import re
from typing import Dict, Any, List
from .base import BaseScanner
from ..plugins import get_plugin_manager
from ..config import settings
from datetime import datetime

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

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs Nmap scan and parses output into structured findings.
        """
        self.update_progress(0.1)

        raw_scan_type = inputs.get("scan_type", "T")
        scan_type, service_detection = self._resolve_scan_type(raw_scan_type)

        plugin_inputs = {
            "target": target,
            "scan_type": scan_type,
            "ports": self._resolve_ports(inputs.get("ports", "")),
            "service_detection": inputs.get("service_detection", service_detection),
            "os_detection": inputs.get("os_detection", False),
            "safe_mode": inputs.get("safe_mode", True),
        }

        plugin_manager = get_plugin_manager()
        command = plugin_manager.build_command("nmap", plugin_inputs)
        
        if not command:
            raise ValueError("Failed to build nmap command")

        # Execute
        self.update_progress(0.2)
        output, exit_code = await self._execute_command(command)
        self.update_progress(0.8)
        
        # Parse
        findings = self._parse_nmap_output(output, target)
        
        self.update_progress(1.0)
        return {
            "findings": findings,
            "summary": [f"Scanned {target} for open ports.", f"Discovered {len(findings)} open ports."],
            "open_ports": [f["metadata"]["port"] for f in findings],
            "status": "completed" if exit_code == 0 else "failed"
        }

    @staticmethod
    def _resolve_scan_type(raw: str) -> tuple:
        """Normalize raw scan type to the single-letter code expected by the nmap plugin.

        Returns (scan_type_letter, service_detection_implied) where
        service_detection_implied is True when the raw value requests version probing.
        """
        raw = raw.strip().lstrip("-")
        # '-sV' or 'sV' implies TCP connect + service version detection
        if raw.lower() in ("sv", "v"):
            return "T", True
        # Full nmap flag like 'sS', 'sT', 'sU' — strip the leading 's'
        if raw.lower().startswith("s") and len(raw) > 1:
            letter = raw[1].upper()
        elif len(raw) >= 1:
            letter = raw[0].upper()
        else:
            return "T", False
        return (letter if letter in ("S", "T", "U") else "T"), False

    @staticmethod
    def _resolve_ports(raw: str) -> str:
        """Map convenience shorthand labels to valid numeric port specifications.

        Empty string tells the nmap template to use its --top-ports default.
        Shorthand values like 'top100' and 'all' are mapped to numeric ranges
        accepted by both the nmap CLI and the port-spec validator.
        """
        raw = raw.strip()
        if raw in ("top100", ""):
            return ""        # nmap template emits --top-ports 100
        if raw == "top1000":
            return "1-1000"
        if raw == "all":
            return "1-65535"
        return raw

    async def _execute_command(self, command: List[str]) -> tuple:
        """Executes the command and returns (output, exit_code)"""
        import asyncio.subprocess
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        try:
            stdout, _ = await process.communicate()
            return stdout.decode('utf-8', errors='replace'), process.returncode
        except asyncio.CancelledError:
            try:
                process.kill()
                await process.wait()
            except Exception:
                pass
            raise

    def _parse_nmap_output(self, output: str, target: str) -> List[Dict[str, Any]]:
        findings = []
        # Regex for open ports: 80/tcp open http
        port_pattern = re.compile(r"(\d+)/(tcp|udp)\s+open\s+([\w-]+)\s*(.*)")
        
        for match in port_pattern.finditer(output):
            port_str, proto, service, version = match.groups()
            
            title = f"Open Port: {port_str}/{proto} ({service})"
            description = f"Port {port_str} is open and running {service} service."
            if version.strip():
                description += f" Version detected: {version.strip()}"
            
            findings.append({
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
                    "version": version.strip()
                }
            })
            
        return findings
