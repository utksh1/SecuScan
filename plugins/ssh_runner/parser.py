from typing import Dict, Any, List

def parse(output: str) -> Dict[str, Any]:
    """
    Parse SSH output (stdout).
    """
    findings = []
    
    # Store the whole output as a summary
    findings.append({
        "title": "SSH Command Executed Successfully",
        "category": "Remote Execution",
        "severity": "info",
        "description": f"Command output:\n{output}",
        "remediation": "Review the command output for any anomalies or security concerns.",
        "metadata": {
            "raw_output": output
        }
    })
    
    # Basic check for common error indicators in output
    if "Permission denied" in output or "Connection refused" in output:
        findings[0]["title"] = "SSH Execution Failed / Error"
        findings[0]["severity"] = "medium"
        
    return {
        "findings": findings,
        "raw_output": output
    }
