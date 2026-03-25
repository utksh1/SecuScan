import json
from typing import List, Dict, Any

def parse(raw_output: str) -> List[Dict[str, Any]]:
    """
    Parses WPScan JSON output into structured findings.
    """
    try:
        data = json.loads(raw_output)
        findings = []
        
        # Parse Interesting Findings
        for finding in data.get("interesting_findings", []):
            findings.append({
                "type": "info",
                "title": finding.get("to_s", "Interesting Finding"),
                "description": f"Interesting finding identified by WPScan: {finding.get('to_s')}",
                "severity": "low",
                "metadata": {
                    "references": finding.get("references", {}),
                    "confidence": finding.get("confidence", 0)
                }
            })
            
        # Parse Vulnerabilities in Plugins
        plugins = data.get("plugins", {})
        for plugin_name, plugin_data in plugins.items():
            for vuln in plugin_data.get("vulnerabilities", []):
                findings.append({
                    "type": "vulnerability",
                    "title": f"WordPress Plugin Vulnerability: {plugin_name}",
                    "description": vuln.get("title", "No description provided"),
                    "severity": "high",
                    "metadata": {
                        "plugin": plugin_name,
                        "version": plugin_data.get("version", {}).get("number"),
                        "references": vuln.get("references", {}),
                        "fixed_in": vuln.get("fixed_in")
                    }
                })
        
        # Parse Vulnerabilities in Themes
        themes = data.get("themes", {})
        for theme_name, theme_data in themes.items():
            for vuln in theme_data.get("vulnerabilities", []):
                findings.append({
                    "type": "vulnerability",
                    "title": f"WordPress Theme Vulnerability: {theme_name}",
                    "description": vuln.get("title", "No description provided"),
                    "severity": "high",
                    "metadata": {
                        "theme": theme_name,
                        "version": theme_data.get("version", {}).get("number"),
                        "references": vuln.get("references", {})
                    }
                })

        return findings
    except Exception as e:
        return [{"type": "error", "title": "Parsing Error", "description": str(e), "severity": "info"}]
