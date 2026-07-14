#!/usr/bin/env python3
"""Backfill explicit capabilities in plugin metadata.json files."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "plugins"

# Explicit capability declarations for bundled plugins missing the field.
PLUGIN_CAPABILITIES: dict[str, list[str]] = {
    "amass": ["network"],
    "cloud_scanner": ["network", "intrusive"],
    "cloud_storage_auditor": ["network"],
    "code_analyzer": ["filesystem"],
    "container_scanner": ["network", "docker"],
    "crawler": ["network", "intrusive"],
    "dir_discovery": ["network", "intrusive", "filesystem"],
    "dns_enum": ["network"],
    "dnsx": ["network"],
    "domain-finder": ["network"],
    "droopescan": ["network", "intrusive"],
    "fuzzer": ["network", "intrusive", "exploit", "filesystem"],
    "google-dorking": ["network"],
    "hashcat": ["filesystem", "intrusive", "exploit"],
    "http_request_logger": ["network", "intrusive"],
    "httpx": ["network"],
    "iac_scanner": ["filesystem"],
    "icmp_ping": ["network"],
    "joomscan": ["network", "intrusive"],
    "katana": ["network", "intrusive"],
    "kubernetes_scanner": ["network", "intrusive"],
    "metasploit": ["network", "intrusive", "exploit", "credentials"],
    "nikto": ["network", "intrusive"],
    "nmap": ["network"],
    "nuclei": ["network", "intrusive"],
    "password_auditor": ["network", "intrusive", "credentials"],
    "people-email-discovery": ["network"],
    "port-scanner": ["network", "intrusive"],
    "scapy_recon": ["network"],
    "secret_scanner": ["filesystem"],
    "semgrep_scanner": ["filesystem"],
    "sharepoint_scanner": ["network", "intrusive"],
    "sitemap_gen": ["network", "intrusive"],
    "spider": ["network", "intrusive"],
    "sqli_checker": ["network", "intrusive"],
    "sqli_exploiter": ["network", "intrusive", "exploit"],
    "sqlmap": ["network", "intrusive", "exploit"],
    "ssh_runner": ["network", "intrusive", "credentials"],
    "subdomain_discovery": ["network"],
    "subdomain_takeover": ["network", "intrusive", "exploit"],
    "subfinder": ["network"],
    "theharvester": ["network"],
    "tls_inspector": ["network"],
    "uncover": ["network"],
    "url-fuzzer-2": ["network", "intrusive", "filesystem"],
    "urlfinder": ["network"],
    "virtual-host-finder": ["network", "intrusive", "filesystem"],
    "volatility": ["filesystem", "intrusive"],
    "website-recon-2": ["network"],
    "whois_lookup": ["network"],
    "wpscan": ["network", "intrusive"],
    "yara_scan": ["filesystem", "intrusive"],
}


def insert_capabilities(metadata: dict, capabilities: list[str]) -> dict:
    ordered: dict = {}
    for key, value in metadata.items():
        if key == "checksum":
            ordered["capabilities"] = capabilities
        ordered[key] = value
    if "capabilities" not in ordered:
        ordered["capabilities"] = capabilities
    return ordered


def main() -> None:
    updated = 0
    for plugin_id, capabilities in sorted(PLUGIN_CAPABILITIES.items()):
        plugin_dir = PLUGINS_DIR / plugin_id
        metadata_file = plugin_dir / "metadata.json"
        if not metadata_file.exists():
            raise SystemExit(f"Missing metadata for plugin: {plugin_id}")

        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        if metadata.get("capabilities") is not None:
            continue

        metadata = insert_capabilities(metadata, capabilities)
        metadata_file.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        updated += 1
        print(f"updated {plugin_id}: {capabilities}")

    print(f"\nUpdated {updated} plugin metadata files.")


if __name__ == "__main__":
    main()
