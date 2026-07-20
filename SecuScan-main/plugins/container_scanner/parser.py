import json
import re
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse Trivy JSON output.
    """
    findings = []
    
    try:
        # Trivy might print some info/warnings before the actual JSON array/object.
        # Find the first valid JSON array or object.
        start_idx = output.find('{')
        if start_idx == -1:
            start_idx = output.find('[')
            
        if start_idx != -1:
            raw_json = output[start_idx:len(output)]
            data = json.loads(raw_json)
            
            # Trivy usually outputs a JSON object with a "Results" array
            if isinstance(data, dict):
                results = data.get("Results", [])
            elif isinstance(data, list):
                results = data
            else:
                results = []
                
            for res in results:
                target_name = res.get("Target", "Unknown Target")
                vulnerabilities = res.get("Vulnerabilities", [])
                
                for vuln in vulnerabilities:
                    cve_id = vuln.get("VulnerabilityID", "Unknown CVE")
                    pkg_name = vuln.get("PkgName", "Unknown Package")
                    title = vuln.get("Title", f"{cve_id} in {pkg_name}")
                    
                    # Normalize severity
                    severity_raw = vuln.get("Severity", "UNKNOWN").lower()
                    if severity_raw == "critical":
                        severity = "critical"
                    elif severity_raw == "high":
                        severity = "high"
                    elif severity_raw == "medium":
                        severity = "medium"
                    elif severity_raw == "low":
                        severity = "low"
                    else:
                        severity = "info"
                        
                    findings.append({
                        "title": title,
                        "category": "Container Vulnerability",
                        "severity": severity,
                        "description": vuln.get("Description", "No description provided."),
                        "remediation": f"Update {pkg_name} to version {vuln.get('FixedVersion', 'N/A')}",
                        "metadata": {
                            "cve": cve_id,
                            "package": pkg_name,
                            "installed_version": vuln.get("InstalledVersion", "N/A"),
                            "fixed_version": vuln.get("FixedVersion", "N/A"),
                            "target": target_name,
                            "cvss": vuln.get("CVSS", {})
                        }
                    })
    except json.JSONDecodeError:
        # Fallback if the JSON was completely corrupted or Trivy failed
        pass
    except Exception as e:
        pass
        
    return {
        "findings": findings
    }
