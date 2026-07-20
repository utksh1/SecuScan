#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
WORDLIST_DIR="$ROOT_DIR/wordlists"
log() {
  printf '%s\n' "$1"
}

download_wordlist() {
  local url="$1"
  local target_path="$2"

  mkdir -p "$WORDLIST_DIR"
  log "Downloading $(basename "$target_path")"
  curl -fsSL "$url" -o "$target_path"
}

update_seclists() {
  download_wordlist "https://raw.githubusercontent.com/daviddias/node-dirbuster/master/lists/directory-list-2.3-medium.txt" "$WORDLIST_DIR/medium.txt"
  download_wordlist "https://raw.githubusercontent.com/daviddias/node-dirbuster/master/lists/directory-list-2.3-big.txt" "$WORDLIST_DIR/large.txt"
  download_wordlist "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/Web-Content/common.txt" "$WORDLIST_DIR/common.txt"
  download_wordlist "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Discovery/DNS/subdomains-top1million-110000.txt" "$WORDLIST_DIR/subdomains-top1million-110000.txt"
}

update_nuclei_assets() {
  if command -v nuclei >/dev/null 2>&1; then
    log "Updating Nuclei templates"
    nuclei -update-templates
  else
    log "Skipping Nuclei template update: nuclei not found"
  fi
}

update_wpscan_db() {
  if command -v wpscan >/dev/null 2>&1; then
    log "Updating WPScan database"
    wpscan --update
  else
    log "Skipping WPScan update: wpscan not found"
  fi
}

main() {
  log "Bootstrapping scanner support assets"
  update_seclists
  update_nuclei_assets
  update_wpscan_db
  log "Scanner support assets are ready"
}

main "$@"
