# AI Executive Summary — Setup & Usage Guide

SecuScan can optionally generate a concise plain-English executive summary at the
top of HTML and PDF scan reports. The summary is produced by an LLM after a scan
completes and is aimed at non-technical stakeholders who need a quick
"what happened and what matters most?" without reading every raw finding.

The feature is **completely opt-in**. When not configured it has zero effect —
reports generate exactly as before, no exceptions, no extra dependencies needed.

---

## How It Works

1. After a scan finishes, `ReportGenerator` calls `_get_ai_summary()` with the
   list of normalised findings.
2. `generate_summary()` in `ai_summary.py` builds a prompt from **metadata only**
   — severity counts, categories, and finding titles. Hostnames, IPs, URLs, and
   credentials are **never** included in the prompt.
3. The LLM returns a 3–5 sentence plain-text paragraph.
4. The summary appears as a highlighted block at the top of the Executive Overview
   section in both HTML and PDF reports.

---

## Structured Output Formats

The AI executive summary is **not** included in all report formats. This section documents the per-format behavior and the reasoning behind it.

### Format Summary

| Format | AI Summary Included | Reason |
|--------|---------------------|--------|
| HTML   | Yes                 | Human-readable; summary improves readability for stakeholders |
| PDF    | Yes                 | Printed/archived reports benefit from the plain-English overview |
| SARIF  | No                  | Machine-readable format for CI integrations; summary would break schema validity |
| JSON   | No                  | Structured export is designed for programmatic consumption; summary would add unstructured noise |

### SARIF Exclusion

SARIF (Static Analysis Results Interchange Format) is a JSON-based standard used by CI tools, security scanners, and IDEs to consume and process scan results programmatically. Adding a free-text AI summary to SARIF output would:

- Break strict schema validation in consuming tools (GitHub Code Scanning, Defender, etc.)
- Add non-deterministic content that varies between LLM calls, complicating reproducible CI results
- Introduce unstructured text into a format designed for structured data

The SARIF report contains the full machine-readable list of findings. CI consumers can extract any metadata they need directly from the structured JSON.

### JSON/CSV Export Exclusion

Bulk JSON and CSV exports are designed for data processing pipelines, database ingestion, or third-party integrations. Including the AI summary would:

- Add unstructured text to structured output formats
- Complicate downstream parsing (summary may contain commas, quotes, newlines)
- Be redundant — the findings data already includes all the metadata the summary is based on

### HTML and PDF Inclusion

HTML and PDF reports are the primary human-facing outputs. The AI summary adds the most value here:

- Non-technical stakeholders can understand scan results without reading raw findings
- The highlighted block at the top of the Executive Overview provides immediate context
- Both formats handle rich text and are not subject to machine-consumption constraints

This design ensures the AI summary reaches the right audience without interfering with machine-consumable outputs.

---

## Configuration

Set these environment variables before starting the backend
(prefix them with `SECUSCAN_` as per the `Settings` class convention):

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECUSCAN_AI_SUMMARY_ENABLED` | Yes (to activate) | `false` | Set to `true` to turn the feature on. |
| `SECUSCAN_AI_SUMMARY_API_KEY` | Yes (when enabled) | _(empty)_ | API key for your LLM provider. |
| `SECUSCAN_AI_SUMMARY_BASE_URL` | No | _(empty → OpenAI)_ | Override for non-OpenAI endpoints. |
| `SECUSCAN_AI_SUMMARY_MODEL` | No | `gpt-4o-mini` | Model name. |

### OpenAI (cloud)

```bash
export SECUSCAN_AI_SUMMARY_ENABLED=true
export SECUSCAN_AI_SUMMARY_API_KEY=sk-...your-key...
export SECUSCAN_AI_SUMMARY_MODEL=gpt-4o-mini
```

### Ollama (local, free, no data leaves your machine)

```bash
ollama pull llama3

export SECUSCAN_AI_SUMMARY_ENABLED=true
export SECUSCAN_AI_SUMMARY_API_KEY=ollama
export SECUSCAN_AI_SUMMARY_BASE_URL=http://localhost:11434/v1
export SECUSCAN_AI_SUMMARY_MODEL=llama3
```

### Any other OpenAI-compatible provider

```bash
export SECUSCAN_AI_SUMMARY_ENABLED=true
export SECUSCAN_AI_SUMMARY_API_KEY=your-key
export SECUSCAN_AI_SUMMARY_BASE_URL=https://api.your-provider.com/v1
export SECUSCAN_AI_SUMMARY_MODEL=provider-model-name
```

---

## Dependency

`openai>=1.0.0` is already added to `backend/requirements.txt`. Install with:

```bash
pip install -r backend/requirements.txt
```

---

## Privacy & Safety

- Only **finding metadata** (severity, category, title) is sent to the LLM.
- Raw hostnames, IPs, URLs, and credentials are **never** included in the prompt.
- For high-sensitivity environments, use a local Ollama instance so no data
  leaves your network.
- If using a cloud provider, review their data-retention policy before enabling.

---

## Disabling

Leave `SECUSCAN_AI_SUMMARY_ENABLED` unset or set it to `false`. Reports will
generate exactly as before. The `openai` package does not need to be installed.

---

## Running the Tests

```bash
# Full backend suite
./testing/test_python.sh

# Targeted
python -m pytest testing/backend/unit/test_ai_summary.py -v
```
