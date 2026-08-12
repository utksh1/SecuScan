import base64
import csv
import html
import io
import json
import re
from .redaction import redact, redact_dict, _redact_value
from .ai_summary import generate_summary
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List

from backend import __version__

from PIL import Image, ImageDraw
from xhtml2pdf import pisa

from .time_utils import format_utc_display, to_utc_iso


class ReportGenerator:
    """Handles PDF, HTML, and CSV generation for security audits."""

    ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
    CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B-\x1F\x7F]")

    SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    SEVERITY_COLORS = {
        "CRITICAL": (153, 27, 27),
        "HIGH": (220, 38, 38),
        "MEDIUM": (217, 119, 6),
        "LOW": (37, 99, 235),
        "INFO": (71, 85, 105),
    }

    @classmethod
    def _generate_severity_chart(cls, severity_counts: Dict[str, int]) -> str:
        """Generate a base64 PNG horizontal bar chart representing the vulnerability distribution."""
        width, height = 480, 160
        img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        colors_map = {k: (*v, 255) for k, v in cls.SEVERITY_COLORS.items()}
        max_val = max(severity_counts.values()) if any(severity_counts.values()) else 1

        # Draw background container
        draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=8, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=1)

        y_offset = 12
        bar_height = 16
        spacing = 10
        x_start = 110
        max_bar_width = 280

        from PIL import ImageFont
        font = None
        for font_name in ("arial.ttf", "Helvetica.ttf", "segoeui.ttf", "sans-serif.ttf"):
            try:
                font = ImageFont.truetype(font_name, 12)
                break
            except Exception:
                continue
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        for i, sev in enumerate(cls.SEVERITY_ORDER):
            count = severity_counts.get(sev, 0)
            bar_len = int((count / max_val) * max_bar_width) if count > 0 else 0
            color = colors_map[sev]

            # Draw background progress track
            draw.rounded_rectangle([x_start, y_offset, x_start + max_bar_width, y_offset + bar_height], radius=4, fill=(226, 232, 240, 255))

            # Draw actual severity bar
            if count > 0:
                draw.rounded_rectangle([x_start, y_offset, x_start + bar_len, y_offset + bar_height], radius=4, fill=color)

            # Draw labels
            if font:
                # Severity label
                draw.text((20, y_offset + 2), sev.title(), fill=(71, 85, 105, 255), font=font)
                # Count label
                draw.text((x_start + bar_len + 10, y_offset + 2), str(count), fill=(15, 23, 42, 255), font=font)

            y_offset += bar_height + spacing

        output = io.BytesIO()
        try:
            img.save(output, format="PNG")
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        finally:
            output.close()

    @classmethod
    def _get_ai_summary(cls, findings):
        """Return an AI executive summary, or '' when the feature is disabled."""
        from .config import settings as _settings
        if not _settings.ai_summary_enabled:
            return ""
        if not _settings.ai_summary_api_key:
            return ""
        return generate_summary(
            findings=findings,
            model=_settings.ai_summary_model,
            api_key=_settings.ai_summary_api_key,
            base_url=_settings.ai_summary_base_url or None,
        )

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = value.strip("#")
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    @staticmethod
    @lru_cache(maxsize=32)
    def _icon_data_uri(name: str, background: str = "1e3a5f", foreground: str = "ffffff") -> str:
        """Return a tiny embedded PNG icon that works in both HTML and xhtml2pdf."""
        bg = ReportGenerator._hex_to_rgb(background)
        fg = ReportGenerator._hex_to_rgb(foreground)
        image = Image.new("RGB", (48, 48), bg)
        draw = ImageDraw.Draw(image)

        if name == "shield":
            draw.line([(24, 8), (36, 13), (34, 28), (24, 39), (14, 28), (12, 13), (24, 8)], fill=fg, width=3)
            draw.line([(19, 24), (23, 28), (30, 19)], fill=fg, width=3)
        elif name == "findings":
            draw.rectangle((12, 11, 36, 37), outline=fg, width=3)
            draw.line((17, 18, 31, 18), fill=fg, width=2)
            draw.line((17, 24, 31, 24), fill=fg, width=2)
            draw.line((17, 30, 27, 30), fill=fg, width=2)
        elif name == "critical":
            draw.polygon([(24, 9), (38, 36), (10, 36)], outline=fg)
            draw.line((24, 17, 24, 27), fill=fg, width=3)
            draw.ellipse((22, 31, 26, 35), fill=fg)
        elif name == "rows":
            for y in (13, 22, 31):
                draw.rectangle((12, y, 36, y + 5), outline=fg, width=2)
        elif name == "clock":
            draw.ellipse((11, 11, 37, 37), outline=fg, width=3)
            draw.line((24, 24, 24, 15), fill=fg, width=3)
            draw.line((24, 24, 31, 28), fill=fg, width=3)
        elif name == "target":
            draw.ellipse((11, 11, 37, 37), outline=fg, width=3)
            draw.ellipse((18, 18, 30, 30), outline=fg, width=2)
            draw.line((24, 7, 24, 15), fill=fg, width=2)
            draw.line((24, 33, 24, 41), fill=fg, width=2)
            draw.line((7, 24, 15, 24), fill=fg, width=2)
            draw.line((33, 24, 41, 24), fill=fg, width=2)
        else:
            draw.ellipse((11, 11, 37, 37), outline=fg, width=3)
            draw.line((24, 18, 24, 30), fill=fg, width=3)
            draw.ellipse((22, 33, 26, 37), fill=fg)

        output = io.BytesIO()
        try:
            image.save(output, format="PNG")
            encoded = base64.b64encode(output.getvalue()).decode("ascii")
            return f"data:image/png;base64,{encoded}"
        finally:
            output.close()

    @classmethod
    def _clean_text(cls, value: Any) -> str:
        if value is None:
            return ""
        text = str(value)
        text = cls.ANSI_ESCAPE_RE.sub("", text)
        text = cls.CONTROL_CHARS_RE.sub("", text)
        return text.strip()

    @classmethod
    def _escape_html(cls, value: Any) -> str:
        return html.escape(cls._clean_text(value), quote=True)

    @classmethod
    def _escape_html_with_breaks(cls, value: Any, break_html: str = "<wbr>") -> str:
        escaped = cls._escape_html(value)
        for delimiter in ("/", "-", "_", ":"):
            escaped = escaped.replace(delimiter, f"{delimiter}{break_html}")
        return escaped

    @classmethod
    def _normalize_finding(cls, finding: Any) -> Dict[str, Any]:
        if not isinstance(finding, dict):
            finding = {"description": cls._clean_text(finding)}

        metadata = finding.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}

        normalized = {
            "id": cls._clean_text(finding.get("id")),
            "title": cls._clean_text(finding.get("title")) or "Untitled finding",
            "category": cls._clean_text(finding.get("category")) or "General",
            "severity": cls._clean_text(finding.get("severity") or "info").upper(),
            "target": redact(cls._clean_text(finding.get("target"))),
            "description": redact(cls._clean_text(finding.get("description")) or "No description was provided."),
            "remediation": redact(cls._clean_text(finding.get("remediation"))),
            "proof": redact(cls._clean_text(finding.get("proof"))),
            "cve": cls._clean_text(finding.get("cve")),
            "cwe": cls._clean_text(finding.get("cwe")),
            "cvss": finding.get("cvss"),
            "validated": bool(finding.get("validated", False)),
            "validation_method": cls._clean_text(finding.get("validation_method")),
            "confidence_reason": redact(cls._clean_text(finding.get("confidence_reason"))),
            "service_fingerprint": cls._clean_text(finding.get("service_fingerprint")),
            "cpe": cls._clean_text(finding.get("cpe")),
            "discovered_at": to_utc_iso(finding.get("discovered_at")) if finding.get("discovered_at") else "",
            "evidence": _redact_value(finding.get("evidence", [])) if isinstance(finding.get("evidence"), list) else [],
            "asset_refs": finding.get("asset_refs", []) if isinstance(finding.get("asset_refs"), list) else [],
            "references": finding.get("references", []) if isinstance(finding.get("references"), list) else [],
            "metadata": redact_dict({cls._clean_text(key): cls._clean_text(val) for key, val in metadata.items()}),
        }
        if normalized["severity"] not in cls.SEVERITY_COLORS:
            normalized["severity"] = "INFO"
        return normalized

    @classmethod
    def _normalize_task_inputs(cls, task: Dict[str, Any]) -> Dict[str, Any]:
        raw_inputs = task.get("inputs")
        if not raw_inputs:
            raw_inputs = task.get("inputs_json")

        if isinstance(raw_inputs, str):
            try:
                raw_inputs = json.loads(raw_inputs)
            except json.JSONDecodeError:
                raw_inputs = {}

        if not isinstance(raw_inputs, dict):
            return {}

        normalized: Dict[str, Any] = {}
        for key, value in raw_inputs.items():
            if value in ("", None, [], {}):
                continue
            normalized[cls._clean_text(key)] = value
        return normalized

    @classmethod
    def _format_input_value(cls, value: Any) -> str:
        if value is True:
            return "ON"
        if value is False:
            return "OFF"
        if isinstance(value, list):
            return ", ".join(cls._clean_text(item) for item in value if cls._clean_text(item))
        if isinstance(value, dict):
            return json.dumps(value, sort_keys=True)
        return cls._clean_text(value)

    @classmethod
    def _build_scan_parameters(cls, task: Dict[str, Any]) -> List[Dict[str, str]]:
        parameters = [
            {"label": "Target", "value": cls._clean_text(task.get("target")) or "Unknown"},
            {"label": "Plugin", "value": cls._clean_text(task.get("plugin_id")) or "Unknown"},
        ]

        preset = cls._clean_text(task.get("preset"))
        if preset:
            parameters.append({"label": "Preset", "value": preset})

        execution_context = task.get("execution_context")
        if not execution_context:
            raw_context = task.get("execution_context_json")
            if isinstance(raw_context, str):
                try:
                    execution_context = json.loads(raw_context)
                except json.JSONDecodeError:
                    execution_context = {}
        if isinstance(execution_context, dict):
            for key in ("target_policy_id", "scan_profile", "credential_profile_id", "session_profile_id", "validation_mode", "evidence_level"):
                value = cls._clean_text(execution_context.get(key))
                if value:
                    parameters.append({"label": key.replace("_", " ").title(), "value": value})

        for key, value in cls._normalize_task_inputs(task).items():
            label = key.replace("_", " ").title()
            formatted = cls._format_input_value(value)
            if formatted:
                parameters.append({"label": label, "value": formatted})

        command_used = cls._clean_text(task.get("command_used"))
        if command_used:
            parameters.append({"label": "Command", "value": command_used})

        return parameters

    @classmethod
    def _build_summary_lines(
        cls,
        findings: List[Dict[str, Any]],
        severity_counts: Dict[str, int],
        structured: Dict[str, Any],
        task: Dict[str, Any],
    ) -> List[str]:
        total_findings = len(findings)
        critical_high = severity_counts.get("CRITICAL", 0) + severity_counts.get("HIGH", 0)
        summary: List[str] = []

        if total_findings == 0:
            summary.append("No structured findings were recorded for this assessment run.")
        elif critical_high > 0:
            summary.append(
                f"The assessment identified {total_findings} findings, including "
                f"{critical_high} high-priority items that should be reviewed first."
            )
        else:
            summary.append(
                f"The assessment identified {total_findings} findings with no critical or high severity items."
            )

        tool_name = cls._clean_text(task.get("tool_name")) or cls._clean_text(task.get("plugin_id")) or "scan engine"
        summary.append(f"Scan execution was performed with {tool_name}.")

        open_ports = structured.get("open_ports")
        if isinstance(open_ports, list) and open_ports:
            summary.append(f"Observed {len(open_ports)} exposed network ports during this run.")

        technologies = structured.get("technologies")
        if isinstance(technologies, list) and technologies:
            summary.append(f"Detected {len(technologies)} technology fingerprints in the target surface.")

        rows = structured.get("rows")
        if isinstance(rows, list) and rows:
            summary.append(f"Structured output included {len(rows)} tabular result rows for analyst review.")

        return summary

    @classmethod
    def _build_report_payload(cls, task: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        structured = result.get("structured")
        if not isinstance(structured, dict):
            structured = result if isinstance(result, dict) else {}

        raw_findings = result.get("findings")
        if not isinstance(raw_findings, list):
            raw_findings = structured.get("findings", []) if isinstance(structured, dict) else []

        findings = [cls._normalize_finding(item) for item in raw_findings]

        severity_counts = {severity: 0 for severity in cls.SEVERITY_ORDER}
        for finding in findings:
            severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1

        raw_summary = result.get("summary")
        if isinstance(raw_summary, list) and raw_summary:
            summary = [cls._clean_text(item) for item in raw_summary if cls._clean_text(item)]
        else:
            summary = cls._build_summary_lines(findings, severity_counts, structured, task)

        rows = structured.get("rows")
        if not isinstance(rows, list):
            rows = []

        errors = result.get("errors")
        if not isinstance(errors, list):
            errors = []

        return {
            "task_id": cls._clean_text(task.get("id")),
            "tool_name": cls._clean_text(task.get("tool_name")) or cls._clean_text(task.get("plugin_id")) or "Unknown tool",
            "target": cls._clean_text(task.get("target")) or "Unknown target",
            "status": cls._clean_text(task.get("status")) or "unknown",
            "created_at": to_utc_iso(task.get("created_at")) if task.get("created_at") else "",
            "generated_at": to_utc_iso(),
            "preset": cls._clean_text(task.get("preset")),
            "findings": findings,
            "summary": summary,
            "severity_counts": severity_counts,
            "structured": structured,
            "rows": rows,
            "errors": errors,
            "scan_parameters": cls._build_scan_parameters(task),
            "command_used": cls._clean_text(task.get("command_used")),
        }

    @staticmethod
    def _format_timestamp(value: str) -> str:
        if not value:
            return "Unknown"
        return format_utc_display(value)

    @classmethod
    def _generate_pdf_html_report(cls, task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generate conservative HTML/CSS that xhtml2pdf can paginate reliably."""
        payload = cls._build_report_payload(task, result)
        findings = payload["findings"]
        severity_counts = payload["severity_counts"]
        ai_summary = cls._get_ai_summary(findings)
        shield_icon = cls._icon_data_uri("shield", "1e3a5f")
        target_icon = cls._icon_data_uri("target", "2563eb")
        findings_icon = cls._icon_data_uri("findings", "0f172a")
        critical_icon = cls._icon_data_uri("critical", "991b1b")
        rows_icon = cls._icon_data_uri("rows", "2563eb")
        clock_icon = cls._icon_data_uri("clock", "475569")
        target_html = cls._escape_html_with_breaks(payload["target"], " ")

        summary_markup = "".join(
            f"<li>{cls._escape_html(line)}</li>" for line in payload["summary"]
        )
        parameter_markup = "".join(
            f"<tr><td><label>{cls._escape_html(item['label'])}</label><strong>{cls._escape_html(item['value'])}</strong></td></tr>"
            for item in payload["scan_parameters"]
        )
        finding_markup = "".join(
            for finding in findings
        )

        if not finding_markup:
            finding_markup = """
        return f"""<!DOCTYPE html>
  <ul>{summary_markup}</ul>

  <h2><img class="stat-icon" src="{clock_icon}" alt=""> Assessment Details</h2>
  <table class="meta-table">
    <tr>
      <td><label>Task ID</label><strong>{cls._escape_html(payload['task_id'] or 'Unknown')}</strong></td>
      <td><label>Started</label><strong>{cls._escape_html(cls._format_timestamp(payload['created_at']))}</strong></td>
    </tr>
    <tr>
      <td><label>Tool</label><strong>{cls._escape_html(payload['tool_name'])}</strong></td>
      <td><label>Status</label><strong>{cls._escape_html(payload['status'].upper())}</strong></td>
    </tr>
  </table>

  <h2><img class="stat-icon" src="{target_icon}" alt=""> Scan Parameters</h2>
  <table class="meta-table">
    {parameter_markup}
  </table>

  <h2><img class="stat-icon" src="{findings_icon}" alt=""> Technical Findings</h2>
  {finding_markup}
</div>
</body>
        Contract:
            - Returns raw PDF bytes on success.
            - Raises RuntimeError("Failed to render SecuScan HTML report as PDF")
              on any render failure (pisa error flag or unexpected exception).
            - The internal BytesIO buffer is always closed before returning or
              raising, regardless of the failure mode.
            - No temporary files are written to disk; if this ever changes, the
              same try/finally guarantee must be preserved.
        payload = cls._build_report_payload(task, result)
        findings = payload["findings"]
        severity_counts = payload["severity_counts"]
        ai_summary = cls._get_ai_summary(findings)
        shield_icon = cls._icon_data_uri("shield", "1e3a5f")
        target_icon = cls._icon_data_uri("target", "2563eb")
        findings_icon = cls._icon_data_uri("findings", "0f172a")
        critical_icon = cls._icon_data_uri("critical", "991b1b")
        rows_icon = cls._icon_data_uri("rows", "2563eb")
        clock_icon = cls._icon_data_uri("clock", "475569")
        target_html = cls._escape_html_with_breaks(payload["target"])
        severity_chart_data = cls._generate_severity_chart(severity_counts)

        summary_markup = "".join(
            f"<li>{cls._escape_html(line)}</li>" for line in payload["summary"]
        )
        parameter_markup = "".join(
            f"<div class=\"meta-card\"><label>{cls._escape_html(item['label'])}</label><strong>{cls._escape_html(item['value'])}</strong></div>"
            for item in payload["scan_parameters"]
        )
        finding_markup = "".join(
            for finding in findings
        )

        if not finding_markup:
            finding_markup = """
        return f"""<!DOCTYPE html>
          <ul class="summary-list">{summary_markup}</ul>
        </div>
        <div class="chart-container" style="flex: 0 0 400px; max-width: 100%;">
          <img src="{severity_chart_data}" alt="Severity Distribution Chart" style="width: 100%; height: auto; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.05);" />
        </div>
      </div>
    </section>

    <section class="section">
      <h2><img class="section-icon" src="{target_icon}" alt="">Scan Parameters</h2>
      <p class="section-copy">Runtime configuration captured for this task, including the selected Nikto flags and SecuScan preset context.</p>
      <div class="meta-grid">{parameter_markup}</div>
    </section>

    <section class="section">
      <h2><img class="section-icon" src="{findings_icon}" alt="">Technical Findings</h2>
      <p class="section-copy">Detailed finding cards with severity context, supporting evidence, and recommended next actions.</p>
      <div class="findings">{finding_markup}</div>
    </section>
  </div>
</body>
        Contract:
            - Returns a UTF-8 CSV string on success.
            - Raises RuntimeError on unexpected generation failure.
            - The internal StringIO buffer is always closed.
        payload = cls._build_report_payload(task, result)
        tool_name = payload["tool_name"]

        severity_map = {
            "CRITICAL": "error",
            "HIGH": "error",
            "MEDIUM": "warning",
            "LOW": "note",
            "INFO": "note"
        }

        rules = []
        rule_indices = {}
        results = []

        for finding in payload["findings"]:
            # Derive a stable, deterministic rule ID from finding-specific identifiers
            raw_rule_id = None

            # 1. Check CVE
            cve = finding.get("cve")
            if cve and isinstance(cve, str) and cve.strip():
                raw_rule_id = cve.strip()

            # 2. Check CWE (direct or in metadata)
            if not raw_rule_id:
                cwe = finding.get("cwe") or finding.get("metadata", {}).get("cwe")
                if cwe and isinstance(cwe, str) and cwe.strip():
                    raw_rule_id = cwe.strip()

            # 3. Check specific check/plugin/finding identifiers
            if not raw_rule_id:
                for key in ["check_id", "plugin_rule_id", "rule_id", "id"]:
                    val = finding.get(key) or finding.get("metadata", {}).get(key)
                    if val and isinstance(val, str) and val.strip():
                        raw_rule_id = val.strip()
                        break

            # 4. Fallback to sanitized title
            if not raw_rule_id:
                raw_rule_id = finding.get("title") or "security-finding"

            # Sanitize raw rule ID (lowercase, replace non-alphanumeric with hyphens)
            rule_id = re.sub(r"[^a-zA-Z0-9\-]", "-", raw_rule_id).lower()
            rule_id = re.sub(r"-+", "-", rule_id).strip("-")
            if not rule_id:
                rule_id = "security-finding"

            if rule_id not in rule_indices:
                rule_indices[rule_id] = len(rules)
                rules.append({
                    "id": rule_id,
                    "name": finding.get("title", "Security Finding"),
                    "shortDescription": {
                        "text": finding.get("title", "Security Finding")
                    },
                    "fullDescription": {
                        "text": finding.get("description", "No detailed description available.")
                    },
                    "help": {
                        "text": finding.get("remediation", "No remediation provided.")
                    },
                    "properties": {
                        "precision": "high",
                        "cpe": finding.get("cpe"),
                        "validated": finding.get("validated"),
                        "validation_method": finding.get("validation_method"),
                    }
                })

            sarif_result = {
                "ruleId": rule_id,
                "ruleIndex": rule_indices[rule_id],
                "message": {
                    "text": finding.get("description", "Security finding detected")
                },
                "level": severity_map.get(finding["severity"], "note"),
                "locations": [],
                "properties": {
                    "confidenceReason": finding.get("confidence_reason"),
                    "cpe": finding.get("cpe"),
                    "validated": finding.get("validated"),
                    "assetRefs": finding.get("asset_refs", []),
                },
            }

            # Attempt to extract location if available
            target = finding.get("target") or payload["target"]
            if target:
                is_url = "://" in target or target.startswith(("http://", "https://"))

                location = {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": target
                        }
                    }
                }

                # If target has a line number like file.py:123 and is NOT a web URL
                if not is_url and ":" in target:
                    parts = target.split(":")
                    if parts[-1].isdigit():
                        location["physicalLocation"]["artifactLocation"]["uri"] = ":".join(parts[:-1])
                        location["physicalLocation"]["region"] = {
                            "startLine": int(parts[-1])
                        }

                sarif_result["locations"].append(location)

            results.append(sarif_result)

        sarif_output = {
            "$schema": "https://schemastore.azurewebsites.net/schemas/json/sarif-2.1.0-rtm.5.json",
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": tool_name,
                            "version": "1.0.0",
                            "informationUri": "https://github.com/utksh1/SecuScan",
                            "rules": rules,
                            "properties": {
                                "generatorVersion": __version__,
                            },
                        }
                    },
                    "properties": {
                        "pluginId": task.get("plugin_id"),
                        "exportTimestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "results": results
                }
            ]
        }

        return json.dumps(sarif_output, indent=2)


reporting = ReportGenerator()
