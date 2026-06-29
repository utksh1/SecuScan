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
3. The LLM returns a 3–5 sentence plain-text paragraph (free-form prose — see
   [Output Format and Structured-Output Caveats](#output-format-and-structured-output-caveats)).
4. The summary appears as a highlighted block at the top of the Executive Overview
   section in both HTML and PDF reports. SARIF is left untouched.

---

## Output Format and Structured-Output Caveats

The summary is **free-form prose, not structured output.** This matters if you expect
JSON, a fixed schema, or machine-parseable fields — none of that is produced or
validated. Keep the following in mind:

- **Plain text only — no schema, no JSON mode.** `generate_summary()` calls the
  provider's `chat.completions` endpoint with a prose instruction ("3–5 sentences,
  plain text, no markdown") and **no** `response_format`, JSON / structured-output mode,
  function / tool calling, or output schema. Don't build tooling that parses the summary
  as structured data.
- **The reply is embedded as-is — not parsed or validated.** The model's text is only
  `.strip()`-ed and HTML-escaped before it is dropped into the Executive Overview block
  of the HTML/PDF report. There is no shape check. If a model ignores the "no markdown"
  instruction (smaller or local models often do), bullets or `**bold**` can appear
  verbatim in the report — they are escaped, not stripped.
- **Non-deterministic.** Generation runs at `temperature=0.4`, so the same scan can
  produce a different summary on each report. Treat it as advisory, not a stable
  artifact to diff or snapshot.
- **Length is capped and may truncate.** Responses are limited to `max_tokens=300`.
  The "3–5 sentence" length is a prompt instruction, not a guarantee; a verbose model
  can be cut off mid-sentence.
- **Best-effort, with a silent empty fallback.** If the feature is disabled, the API
  key is missing, the `openai` package is not installed, or the call errors / times out,
  `generate_summary()` returns an empty string and the report simply **omits** the
  summary block (no error is surfaced to the reader). Never assume a summary is present.
- **Advisory, and may be wrong.** The prompt is built from finding *metadata* only
  (severity counts, categories, sanitized titles — see the **Privacy & Safety** section
  below), so the model cannot cite specifics and may still hallucinate. As everywhere in
  SecuScan, this is **automated guidance — manual validation required.**

> **Need structured / machine-readable output?** It is **not supported today.** Producing
> validated JSON would require code changes in `backend/secuscan/ai_summary.py` (e.g.
> setting `response_format` or a JSON schema and then parsing + validating the result),
> and note that many OpenAI-compatible providers (Ollama and others) support JSON /
> structured modes inconsistently or not at all. The source of truth for current behavior
> is `backend/secuscan/ai_summary.py`; see also [Configuration](#configuration).

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
