"""
SecuScan CLI - Command line interface for running security scans
"""

import asyncio
import argparse
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.secuscan.executor import executor
from backend.secuscan.database import init_db, get_db
from backend.secuscan.cache import init_cache
from backend.secuscan.config import settings
from backend.secuscan.plugins import init_plugins, get_plugin_manager
from backend.secuscan.reporting import reporting

async def run_scan(target: str, plugin_id: str, output_format: str, output_file: Optional[str] = None):
    """Initialize components and execute a scan task."""

    # Ensure directories exist
    settings.ensure_directories()

    # Initialize backend components
    await init_db(settings.database_path)
    await init_cache()
    await init_plugins(settings.plugins_dir)

    plugin_manager = get_plugin_manager()

    # If target is "." and no plugin specified, default to a sensible one for code
    if target == "." and plugin_id == "nmap":
        # Check if we should use secret_scanner or code_analyzer instead
        plugin_id = "secret_scanner" if plugin_manager.get_plugin("secret_scanner") else "code_analyzer"
        print(f"[*] Detected directory target '.', defaulting to plugin: {plugin_id}")

    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        print(f"Error: Plugin '{plugin_id}' not found.")
        available = ", ".join(list(plugin_manager.plugins.keys())[:10])
        print(f"Available plugins include: {available}...")
        return 1

    # Create task
    safe_mode = bool(settings.safe_mode_default)
    inputs = {"target": target, "safe_mode": safe_mode}
    try:
        task_id = await executor.create_task(plugin_id, inputs, safe_mode=safe_mode, consent_granted=True)
    except Exception as e:
        print(f"Error creating task: {e}")
        return 1

    print(f"[*] Starting scan {task_id}")
    print(f"[*] Tool: {plugin.name}")
    print(f"[*] Target: {target}")
    print("-" * 40)

    # Execute task
    # We subscribe to broadcast to show live output
    queue = executor.subscribe(task_id)

    execution_task = asyncio.create_task(executor.execute_task(task_id))

    async def monitor_output():
        try:
            while not execution_task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.2)
                    if event["type"] == "output":
                        print(event["data"], end="", flush=True)
                    elif event["type"] == "status":
                        if event["data"] in ["completed", "failed", "cancelled"]:
                            break
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass

    await monitor_output()
    await execution_task

    # Get results
    db = await get_db()
    task_row = await db.fetchone(
        "SELECT id, plugin_id, tool_name, target, status, created_at, preset, inputs_json, command_used, structured_json FROM tasks WHERE id = ?",
        (task_id,)
    )

    if not task_row:
        print("Error: Task record not found after execution.")
        return 1

    if task_row["status"] == "failed":
        print(f"\n[!] Scan failed. Check logs for details.")
        return 1

    print(f"\n[*] Scan completed successfully.")

    # Generate report
    structured_data = json.loads(task_row["structured_json"]) if task_row["structured_json"] else {}
    result_payload = {"structured": structured_data}

    report_content: str = ""
    if output_format == "sarif":
        report_content = reporting.generate_sarif_report(dict(task_row), result_payload)
    elif output_format == "json":
        report_content = json.dumps(structured_data, indent=2)
    elif output_format == "csv":
        report_content = reporting.generate_csv_report(dict(task_row), result_payload)
    elif output_format == "html":
        report_content = reporting.generate_html_report(dict(task_row), result_payload)
    else:
        # Console summary
        findings = structured_data.get("findings", [])
        print(f"[*] Found {len(findings)} issues.")
        for f in findings:
            print(f"  - [{f.get('severity', 'INFO').upper()}] {f.get('title')}")
        return 0

    if output_file:
        output_path = Path(output_file)
        output_path.write_text(report_content)
        print(f"[*] Report saved to: {output_path.absolute()}")
    else:
        print("\n--- Report Output ---")
        print(report_content)

    return 0

def main():
    parser = argparse.ArgumentParser(description="SecuScan CLI - Local-First Pentesting Toolkit")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Run a security scan")
    scan_parser.add_argument("target", help="Target to scan (IP, Domain, or Path)")
    scan_parser.add_argument("--plugin", default="nmap", help="Plugin ID to use (default: nmap)")
    scan_parser.add_argument("--format", choices=["sarif", "json", "csv", "html", "console"], default="console", help="Output format")
    scan_parser.add_argument("--output", "-o", help="Output file path")

    # List plugins command
    subparsers.add_parser("plugins", help="List available plugins")

    args = parser.parse_args()

    if args.command == "scan":
        sys.exit(asyncio.run(run_scan(args.target, args.plugin, args.format, args.output)))
    elif args.command == "plugins":
        # Synchronous shortcut for listing
        async def list_plugins():
            await init_plugins(settings.plugins_dir)
            pm = get_plugin_manager()
            print(f"{'ID':<20} {'Name':<30} {'Category':<15}")
            print("-" * 65)
            for p_id, p in pm.plugins.items():
                print(f"{p_id:<20} {p.name:<30} {p.category:<15}")
        asyncio.run(list_plugins())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
