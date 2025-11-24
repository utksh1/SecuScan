# Wordlists for Directory Discovery

This directory contains wordlists used by the Directory Discovery plugin for web enumeration.

## Available Wordlists

### small.txt (108 entries)
- **Size:** ~108 common paths
- **Use Case:** Fast, polite scanning
- **Duration:** 1-2 minutes
- **Contents:** Most common web directories, admin panels, configuration files

### medium.txt (Not included - External)
- **Size:** ~5,000 entries
- **Use Case:** Balanced discovery
- **Duration:** 5-10 minutes
- **Source:** Download from SecLists or similar

### large.txt (Not included - External)
- **Size:** ~50,000 entries
- **Use Case:** Comprehensive enumeration
- **Duration:** 30+ minutes
- **Source:** Download from SecLists or similar

## Installing Additional Wordlists

### Option 1: Download SecLists

```bash
cd /Users/Apple/secuscan/wordlists
git clone https://github.com/danielmiessler/SecLists.git
ln -s SecLists/Discovery/Web-Content/directory-list-2.3-medium.txt medium.txt
ln -s SecLists/Discovery/Web-Content/directory-list-2.3-big.txt large.txt
```

### Option 2: Custom Wordlists

Place your own wordlists in this directory:
- `medium.txt` - 1,000 to 10,000 entries
- `large.txt` - 10,000+ entries

## Usage in SecuScan

The Directory Discovery plugin automatically uses these wordlists based on the selected preset:
- **Quick** → small.txt
- **Standard** → medium.txt
- **Deep** → large.txt

## Format

Each wordlist should contain one path per line:
```
admin
api
backup
config
```

No leading slashes - the plugin adds them automatically.

## Legal Notice

⚠️ Only use these wordlists to scan systems you own or have explicit permission to test. Unauthorized scanning may be illegal.
