# Plugin Development Walkthrough

## Introduction

This guide helps contributors create a new SecuScan plugin.

## Plugin Structure

plugins/example_plugin/
├── metadata.json
└── parser.py

## Step 1: Create metadata.json

Example:

{
  "id": "example_plugin",
  "name": "Example Plugin",
  "category": "recon",
  "safety_level": "safe"
}

## Step 2: Create parser.py

Example:

def parse(output):
    return {
        "findings": [],
        "raw_output": output
    }

## Validation

python scripts/validate_plugins.py

python scripts/validate_plugin.py --plugin example_plugin

## Refresh Checksum

python scripts/refresh_plugin_checksum.py --plugin example_plugin

## Common Mistakes

- Missing metadata fields
- Invalid safety level
- Incorrect parser output

## Conclusion

You are now ready to contribute a plugin.