import re
from typing import Dict, Any

def parse(output: str) -> Dict[str, Any]:
    """
    Parse sqlmap stdout for vulnerabilities.
    """
    findings = []
    metadata = {}
    
    # Check for injectable parameters
    if "is vulnerable" in output:
        # Try to find the parameter and type
        param_match = re.search(r"Parameter: (.*) \((.*)\)", output)
        if param_match:
            param_name = param_match.group(1).strip()
            param_type = param_match.group(2).strip()
            
            findings.append({
                "title": f"SQL Injection Vulnerability: {param_name}",
                "category": "Injection",
                "severity": "critical",
                "description": f"The parameter '{param_name}' is vulnerable to {param_type}.",
                "remediation": "Use prepared statements, parameterized queries, or an ORM to properly sanitize user inputs. Implement strict input validation.",
                "metadata": {
                    "parameter": param_name,
                    "type": param_type
                }
            })
        else:
            findings.append({
                "title": "Unspecified SQL Injection Vulnerability",
                "category": "Injection",
                "severity": "critical",
                "description": "SQLMap confirmed that the target is vulnerable to SQL injection, but the specific parameter could not be parsed from stdout.",
                "remediation": "Review the full SQLMap log and secure all data input points."
            })

    # Extract database info if available
    if db_match := re.search(r"back-end DBMS: (.*)", output):
        metadata["dbms"] = db_match.group(1).strip()
        
    if os_match := re.search(r"web application technology: (.*)", output):
        metadata["tech_stack"] = os_match.group(1).strip()

    return {
        "findings": findings,
        "metadata": metadata
    }
