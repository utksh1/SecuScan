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
        
        # Prepare inputs for the Nmap plugin
        # Map PortScanner inputs to Nmap plugin fields
        plugin_inputs = {
            "target": target,
            "scan_type": inputs.get("scan_type", "-sV"),
            "ports": inputs.get("ports", "top100"),
            "speed": inputs.get("speed", "T4"),
            "safe_mode": inputs.get("safe_mode", True)
        }
        
        # Handle port shortcuts
        if plugin_inputs["ports"] == "top100":
            plugin_inputs["ports"] = "--top-ports 100"
        elif plugin_inputs["ports"] == "top1000":
            plugin_inputs["ports"] = "--top-ports 1000"
        elif plugin_inputs["ports"] == "all":
            plugin_inputs["ports"] = "-p-"

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
            except:
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
