import asyncio
import json
import re
from typing import Dict, Any, List
from .base import BaseScanner
from ..plugins import get_plugin_manager
from ..config import settings
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ReconScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "Reconnaissance Scanner"

    @property
    def category(self) -> str:
        return "Information Gathering"

    async def run(self, target: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        findings = []
        summary = []
        rows = []
        
        tasks = []
        if "." in target and not target.replace(".", "").isdigit():
            tasks.append(self._run_subfinder(target))
        else:
            tasks.append(asyncio.sleep(0, result=[]))
        
        tasks.append(self._run_whois(target))
        tasks.append(self._run_dns_enum(target))
        
        self.update_progress(0.1)
        results = await asyncio.gather(*tasks, return_exceptions=True)
        self.update_progress(0.9)
        
        sub_findings, whois_findings, dns_findings = results
        
        if not isinstance(sub_findings, Exception) and sub_findings:
            findings.extend(sub_findings)
            for f in sub_findings:
                if f.get("metadata"):
                    rows.append({
                        "tool": "SUBDOMAIN",
                        "subdomain": f["metadata"].get("subdomain"),
                        "details": f.get("description")
                    })
            summary.append(f"Discovered {len(sub_findings)} subdomains.")
        
        if not isinstance(whois_findings, Exception) and whois_findings:
            findings.extend(whois_findings)
            for f in whois_findings:
                if f.get("metadata"):
                    meta = f["metadata"]
                    rows.append({
                        "tool": "WHOIS",
                        "registrar": meta.get("registrar") or meta.get("registrar_name", "N/A"),
                        "organization": meta.get("org") or meta.get("organization", "N/A"),
                        "expiry": str(meta.get("expiration_date", "N/A")).split(' ')[0]
                    })
            summary.append("Retrieved WHOIS registration records.")
        
        if not isinstance(dns_findings, Exception) and dns_findings:
            findings.extend(dns_findings)
            for f in dns_findings:
                if f.get("metadata"):
                    meta = f["metadata"]
                    rows.append({
                        "tool": "DNS",
                        "record": meta.get("record_type", "N/A"),
                        "value": meta.get("value", "N/A"),
                        "details": f.get("description", "N/A")
                    })
            summary.append(f"Discovered {len(dns_findings)} DNS records.")
        
        self.update_progress(1.0)
        return {
            "findings": findings,
            "rows": rows,
            "summary": summary,
            "status": "completed"
        }

    async def _run_subfinder(self, target: str) -> List[Dict[str, Any]]:
        pm = get_plugin_manager()
        cmd = pm.build_command("subdomain_discovery", {"target": target})
        if not cmd: return []
        
        output, _ = await asyncio.wait_for(self._execute_command(cmd), timeout=120)
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
        
        output, _ = await asyncio.wait_for(self._execute_command(cmd), timeout=120)
        
        try:
            data = json.loads(output)
            registrar = data.get("registrar") or data.get("registrar_name", "Unknown")
            expiry = data.get("expiration_date")
            if isinstance(expiry, list):
                expiry = expiry[0]
            
            return [{
                "title": "WHOIS Registration Data",
                "category": "Domain Intelligence",
                "severity": "info",
                "target": target,
                "description": f"Registrar: {registrar}\nExpiry: {expiry if expiry else 'Unknown'}",
                "metadata": data
            }]
        except Exception:
            # Fallback to regex if JSON parsing fails (e.g. legacy output)
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
        
        output, _ = await asyncio.wait_for(self._execute_command(cmd), timeout=120)
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
