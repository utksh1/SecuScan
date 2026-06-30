import json
import sys
import tempfile
import subprocess
import os
import shutil


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No target URL provided", "findings": [], "count": 0}))
        sys.exit(1)

    target = sys.argv[1]
    work_dir = tempfile.mkdtemp(prefix="zap_scan_")
    json_path = os.path.join(work_dir, "output.json")

    try:
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{work_dir}:/zap/wrk:rw",
            "-t", "ghcr.io/zaproxy/zaproxy:stable",
            "zap-full-scan.py",
            "-t", target,
            "-j", "-J", "/zap/wrk/output.json",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )

        findings = []
        if os.path.exists(json_path):
            with open(json_path) as f:
                zap_output = json.load(f)
            if isinstance(zap_output, list):
                findings = zap_output
            elif isinstance(zap_output, dict):
                site = zap_output.get("site", [])
                if isinstance(site, list):
                    for s in site:
                        alerts = s.get("alerts", [])
                        for alert in alerts:
                            findings.append({
                                "title": alert.get("name", "Unknown"),
                                "severity": alert.get("riskdesc", "info").split(" ")[0].lower(),
                                "description": alert.get("desc", ""),
                                "remediation": alert.get("solution", ""),
                                "metadata": {
                                    "url": alert.get("url", ""),
                                    "param": alert.get("param", ""),
                                    "cweid": alert.get("cweid", ""),
                                },
                            })

        output = {
            "findings": findings,
            "count": len(findings),
            "items": findings,
            "stderr": result.stderr[:2000],
        }
        print(json.dumps(output))

    except subprocess.TimeoutExpired:
        print(json.dumps({
            "error": "ZAP scan timed out after 10 minutes",
            "findings": [],
            "count": 0,
        }))
        sys.exit(1)
    except FileNotFoundError:
        print(json.dumps({
            "error": "Docker not found. Ensure Docker is installed and in PATH.",
            "findings": [],
            "count": 0,
        }))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "findings": [],
            "count": 0,
        }))
        sys.exit(1)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
