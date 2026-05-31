# Plugin Health & Coverage Dashboard

The Plugin Health & Coverage Dashboard is a developer utility for inspecting SecuScan plugins.

It follows the repository plugin model by treating plugin directories containing `metadata.json` as the source of truth and checking whether each plugin has a corresponding `parser.py`.

## What it checks

- Total plugin count
- Parser availability
- Plugin category distribution
- Plugin metadata path
- Plugin directory path

## How to run

Print a Markdown report to the terminal:

```bash
python scripts/plugin_health_dashboard.py
```

Print JSON output:

```bash
python scripts/plugin_health_dashboard.py --format json
```

Write Markdown output to a file:

```bash
python scripts/plugin_health_dashboard.py --output plugin_health_report.md
```

Write JSON output to a file:

```bash
python scripts/plugin_health_dashboard.py --format json --output plugin_health_report.json
```

## Notes

The script does not write generated reports by default. Reports are printed to stdout unless an explicit `--output` path is provided.
