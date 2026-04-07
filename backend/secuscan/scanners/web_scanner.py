import asyncio
import json
import re
from typing import Dict, Any, List
from .base import BaseScanner
from ..plugins import get_plugin_manager
from ..config import settings
from datetime import datetime

class WebScanner(BaseScanner):
    """
    Orchestrates DAST scanning (Nikto, Nuclei, FFUF).
    Equivalent to Pentest-Tools 'Website Scanner'.
    """

    @property
    def name(self) -> str:
        return "Web Application Scanner"

    @property
    def category(self) -> str:
        return "Web Security"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes web vulnerability tasks and aggregates findings based on intensity.
        """
        intensity = inputs.get("scan_intensity", "light")
        findings = []
        summary = [f"Performing {intensity} web scan on {target}"]
        
        # 1. HTTP Inspection (Technology Fingerprinting)
        self.update_progress(0.1)
        tech_findings = await self._run_http_inspector(target)
        findings.extend(tech_findings)
        summary.append(f"Identified web technologies and headers.")
        self.update_progress(0.2)

        # 2. Nuclei (Fast Template-based scanning)
        self.update_progress(0.3)
        nuclei_findings = await self._run_nuclei(target)
        findings.extend(nuclei_findings)
        summary.append(f"Discovered {len(nuclei_findings)} vulnerabilities via template scanning.")
        self.update_progress(0.5)

        # 3. Nikto (Comprehensive web server scan) - Deep only
        if intensity in ["deep", "custom"]:
            self.update_progress(0.6)
            nikto_findings = await self._run_nikto(target)
            findings.extend(nikto_findings)
            summary.append(f"Completed comprehensive web server audit.")
            self.update_progress(0.8)

        # 4. FFUF (Directory Discovery) - Deep only
        if intensity in ["deep", "custom"]:
            self.update_progress(0.85)
            dir_findings = await self._run_ffuf(target)
            findings.extend(dir_findings)
            summary.append(f"Enumerated common paths and hidden directories.")
            self.update_progress(1.0)

        self.update_progress(1.0)
        return {
            "findings": findings,
            "summary": summary,
            "status": "completed"
        }

    async def _run_http_inspector(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("http_inspector", {"target": target})
        if not cmd: return []
        output, _ = await self._execute_command(cmd)
        
        findings = []
        if match := re.search(r"(?i)Server:\s*(.*)", output):
            findings.append({
                "title": f"Web Server Disclosed: {match.group(1).strip()}",
                "category": "Information Disclosure",
                "severity": "info",
                "target": target,
                "description": f"The web server discloses its version: {match.group(1).strip()}",
                "metadata": {"server": match.group(1).strip()}
            })
        return findings

    async def _run_nuclei(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        # Ensure we use JSON output for easier parsing if available
        cmd = pm.build_command("nuclei", {"target": target, "silent": True})
        if not cmd: return []
        
        output, _ = await self._execute_command(cmd)
        findings = []
        # Nuclei result pattern: [template-id] [severity] [url] [message]
        for line in output.splitlines():
            if match := re.match(r"\[(.*?)\] \[(.*?)\] \[(.*?)\] (.*)", line):
                tid, sev, url, msg = match.groups()
                findings.append({
                    "title": f"Nuclei: {msg}",
                    "category": "Vulnerability",
                    "severity": self.normalize_severity(sev),
                    "target": target,
                    "description": f"Template {tid} detected a {sev} issue on {url}.",
                    "metadata": {"template": tid, "url": url}
                })
        return findings

    async def _run_nikto(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("nikto", {"target": target})
        if not cmd: return []
        output, _ = await self._execute_command(cmd)
        
        findings = []
        for line in output.splitlines():
            if "+ " in line:
                findings.append({
                    "title": "Nikto Observation",
                    "category": "Web Vulnerability",
                    "severity": "medium", # Nikto doesn't categorize well without -Format json
                    "target": target,
                    "description": line.replace("+ ", "").strip(),
                    "metadata": {"source": "nikto"}
                })
        return findings

    async def _run_ffuf(self, target: str) -> List[Dict[str, Any]]:
        # FFUF is usually quiet or complex, we'll implement it as a finding of 'Interesting Paths'
        pm = get_plugin_manager()
        cmd = pm.build_command("dir_discovery", {"target": target})
        if not cmd: return []
        output, _ = await self._execute_command(cmd)
        
        findings = []
        # Extract 200/301 results
        for match in re.finditer(r"\[Status: (\d+), Size: \d+, Words: \d+, Lines: \d+, Duration: \d+ms\]\s*\|\s*URL: (.*)", output):
            status, url = match.groups()
            findings.append({
                "title": f"Discovered Path: {url} (Status {status})",
                "category": "Asset Discovery",
                "severity": "info",
                "target": target,
                "description": f"Accessible path found during fuzzing: {url}",
                "metadata": {"status": status}
            })
        return findings

    async def _execute_command(self, command: List[str]) -> tuple:
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
