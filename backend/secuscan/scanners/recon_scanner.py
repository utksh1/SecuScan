import asyncio
import json
import re
from typing import Dict, Any, List
from .base import BaseScanner
from ..plugins import get_plugin_manager
from ..config import settings
from datetime import datetime

class ReconScanner(BaseScanner):
    """
    Orchestrates multiple reconnaissance tools (Subfinder, WHOIS, DNS).
    Equivalent to Pentest-Tools 'Recon Tools'.
    """

    @property
    def name(self) -> str:
        return "Reconnaissance Scanner"

    @property
    def category(self) -> str:
        return "Information Gathering"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes multiple recon tasks and aggregates findings.
        """
        findings = []
        summary = [f"Performing reconnaissance on {target}"]
        
        # 1. Subdomain Discovery (if applicable)
        if "." in target and not target.replace(".", "").isdigit():
            self.update_progress(0.1)
            sub_findings = await self._run_subfinder(target)
            findings.extend(sub_findings)
            summary.append(f"Discovered {len(sub_findings)} subdomains.")
            self.update_progress(0.4)

        # 2. WHOIS
        self.update_progress(0.5)
        whois_findings = await self._run_whois(target)
        findings.extend(whois_findings)
        summary.append("Retrieved WHOIS registration records.")
        self.update_progress(0.7)

        # 3. DNS Enum
        self.update_progress(0.8)
        dns_findings = await self._run_dns_enum(target)
        findings.extend(dns_findings)
        summary.append(f"Enumerated {len(dns_findings)} DNS records.")
        self.update_progress(1.0)

        return {
            "findings": findings,
            "summary": summary,
            "status": "completed"
        }

    async def _run_subfinder(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("subdomain_discovery", {"target": target})
        if not cmd: return []
        
        output, _ = await self._execute_command(cmd)
        findings = []
        for line in output.splitlines():
            if line.strip() and "." in line:
                findings.append({
                    "title": f"Subdomain Discovered: {line.strip()}",
                    "category": "Asset Discovery",
                    "severity": "info",
                    "target": target,
                    "description": f"Found subdomain for {target}: {line.strip()}",
                    "metadata": {"subdomain": line.strip()}
                })
        return findings

    async def _run_whois(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("whois_lookup", {"target": target})
        if not cmd: return []
        
        output, _ = await self._execute_command(cmd)
        # Parse basic fields from WHOIS output
        registrar = re.search(r"Registrar:\s*(.*)", output, re.IGNORECASE)
        expiry = re.search(r"Registry Expiry Date:\s*(.*)", output, re.IGNORECASE)
        
        return [{
            "title": "WHOIS Registration Data",
            "category": "Domain Intelligence",
            "severity": "info",
            "target": target,
            "description": f"Registrar: {registrar.group(1).strip() if registrar else 'Unknown'}\n"
                           f"Expiry: {expiry.group(1).strip() if expiry else 'Unknown'}",
            "metadata": {"raw_whois": output[:1000]}
        }]

    async def _run_dns_enum(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("dns_enum", {"target": target})
        if not cmd: return []
        
        output, _ = await self._execute_command(cmd)
        findings = []
        # Look for A, MX, NS records
        patterns = {
            "A Record": r"(?i)A\s+([\d\.]+)",
            "MX Record": r"(?i)MX\s+(.*)",
            "NS Record": r"(?i)NS\s+(.*)"
        }
        
        for name, pattern in patterns.items():
            for match in re.finditer(pattern, output):
                findings.append({
                    "title": f"DNS {name}: {match.group(1).strip()}",
                    "category": "DNS Configuration",
                    "severity": "info",
                    "target": target,
                    "description": f"Discovered {name} pointing to {match.group(1).strip()}",
                    "metadata": {"record_type": name, "value": match.group(1).strip()}
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
