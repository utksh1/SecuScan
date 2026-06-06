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

## UI Dashboard

SecuScan also provides a browser-based Plugin Health Dashboard at **`/plugins`** in the frontend.

### Health states

| State | Meaning |
| --- | --- |
| **Runnable** | Plugin is fully available and can be executed |
| **Degraded** | Plugin is missing one or more system binaries, such as `nmap` or `nikto` |
| **Blocked** | Plugin is blocked by operator capability policy, such as `SECUSCAN_DENIED_CAPABILITIES=exploit` |

### Navigation

Access the dashboard from the sidebar under **Monitor → Plugin Health**, or navigate directly to `/plugins`.

Each plugin card shows:
- Health state badge
- Plugin category and safety level
- Missing binary dependencies (degraded plugins)
- Operator guidance message where available
- Click-through to the plugin's configuration page

### Operator capability policy

Plugins can be blocked at the operator level by setting the `SECUSCAN_DENIED_CAPABILITIES` environment variable. For example:

```bash
SECUSCAN_DENIED_CAPABILITIES=exploit,intrusive
```

Plugins requiring denied capabilities will appear in the **Blocked** group on the dashboard.
See `docs/plugin-validation.md` for the full list of supported capabilities.
