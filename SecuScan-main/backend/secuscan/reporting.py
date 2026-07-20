import base64
import csv
import html
import io
import json
import re
from .redaction import redact, redact_dict
from .ai_summary import generate_summary
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List

from backend import __version__

from PIL import Image, ImageDraw
from xhtml2pdf import pisa


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

        colors_map = {
            "CRITICAL": (153, 27, 27, 255),
            "HIGH": (220, 38, 38, 255),
            "MEDIUM": (217, 119, 6, 255),
            "LOW": (37, 99, 235, 255),
            "INFO": (71, 85, 105, 255)
        }

        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
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

        for i, sev in enumerate(severities):
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
            "target": cls._clean_text(finding.get("target")),
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
            "discovered_at": cls._clean_text(finding.get("discovered_at")),
            "evidence": finding.get("evidence", []) if isinstance(finding.get("evidence"), list) else [],
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
            "created_at": cls._clean_text(task.get("created_at")),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
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
        for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value.replace("Z", ""), fmt).strftime("%b %d, %Y %H:%M")
            except ValueError:
                continue
        return value

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
            f"""
            <div class="finding">
              <table class="finding-header">
                <tr>
                  <td class="severity severity-{finding['severity'].lower()}"><img class="severity-icon" src="{critical_icon}" alt=""> {cls._escape_html(finding['severity'])}</td>
                  <td>
                    <h3>{cls._escape_html(finding['title'])}</h3>
                    <p>{cls._escape_html(finding['category'])} | {cls._escape_html_with_breaks(finding['target'] or payload['target'], " ")}</p>
                  </td>
                </tr>
              </table>
              <h4>Description</h4>
              <p>{cls._escape_html(finding['description'])}</p>
              {f"<h4>Evidence</h4><pre>{cls._escape_html(finding['proof'])}</pre>" if finding['proof'] else ""}
              {f"<p class='meta'>Validated: {'YES' if finding['validated'] else 'NO'}</p>" if finding['validated'] or finding['validation_method'] else ""}
              {f"<p class='meta'>Validation method: {cls._escape_html(finding['validation_method'])}</p>" if finding['validation_method'] else ""}
              {f"<p class='meta'>CPE: {cls._escape_html(finding['cpe'])}</p>" if finding['cpe'] else ""}
              {f"<p class='meta'>Evidence items: {len(finding['evidence'])}</p>" if finding['evidence'] else ""}
              {f"<div class='remediation'><h4>Recommended action</h4><p>{cls._escape_html(finding['remediation'])}</p></div>" if finding['remediation'] else ""}
              {f"<p class='meta'>CVE: {cls._escape_html(finding['cve'])}</p>" if finding['cve'] else ""}
            </div>
            """
            for finding in findings
        )

        if not finding_markup:
            finding_markup = """
            <div class="finding">
              <h3>No structured findings were available</h3>
              <p>This report finished without parsed findings. Review the raw task output in SecuScan for more detail.</p>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>SecuScan Report - {cls._escape_html(payload['target'])}</title>
  <style>
    @page {{
      size: a4 portrait;
      margin: 18mm 14mm 16mm 14mm;
    }}
    html {{
      background-color: #ffffff;
    }}
    body {{
      background-color: #ffffff;
      color: #0f172a;
      font-family: Helvetica, Arial, sans-serif;
      font-size: 10px;
      line-height: 1.45;
      margin: 0;
    }}
    table,
    tr,
    td,
    h1,
    h2,
    h3,
    h4,
    p,
    ul,
    li {{
      background-color: #ffffff;
    }}
    .page {{
      background-color: #ffffff;
      padding: 8px;
    }}
    .brand-table {{
      border-collapse: collapse;
      margin-bottom: 8px;
      width: 100%;
    }}
    .brand-icon {{
      width: 34px;
    }}
    .brand-icon img {{
      height: 30px;
      width: 30px;
    }}
    h1 {{
      color: #0f172a;
      font-size: 20px;
      line-height: 1.18;
      margin: 0;
      padding: 4px 0 8px;
      word-wrap: break-word;
    }}
    h2 {{
      background-color: #f8fafc;
      border-bottom: 1px solid #cbd5e1;
      color: #0f172a;
      font-size: 15px;
      margin: 0;
      padding: 12px 0 4px;
    }}
    h3 {{
      color: #0f172a;
      font-size: 12px;
      margin: 0 0 3px;
    }}
    h4 {{
      color: #0f172a;
      font-size: 10px;
      margin: 10px 0 4px;
    }}
    p {{
      margin: 0;
      padding: 0 0 7px;
    }}
    ul {{
      margin: 0;
      padding: 0 0 8px 16px;
    }}
    pre {{
      background: #f8fafc;
      border: 1px solid #cbd5e1;
      font-family: Courier, monospace;
      font-size: 8px;
      line-height: 1.35;
      margin: 0;
      padding: 8px;
      white-space: pre-wrap;
    }}
    .eyebrow {{
      color: #2563eb;
      font-size: 9px;
      font-weight: bold;
      letter-spacing: 1px;
      text-transform: uppercase;
    }}
    .muted {{
      color: #475569;
    }}
    .stats {{
      border-collapse: collapse;
      margin: 8px 0;
      width: 100%;
    }}
    .stats td {{
      background-color: #ffffff;
      border: 1px solid #cbd5e1;
      padding: 8px;
      width: 25%;
    }}
    .stats label {{
      color: #64748b;
      display: block;
      font-size: 8px;
      text-transform: uppercase;
    }}
    .stats strong {{
      color: #0f172a;
      display: block;
      font-size: 18px;
      margin-top: 4px;
    }}
    .stat-icon {{
      height: 18px;
      width: 18px;
    }}
    .meta-table {{
      border-collapse: collapse;
      margin: 8px 0 0;
      width: 100%;
    }}
    .meta-table td {{
      background-color: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      padding: 7px 4px;
      width: 50%;
    }}
    .meta-table label {{
      color: #64748b;
      display: block;
      font-size: 8px;
      text-transform: uppercase;
    }}
    .meta-table strong {{
      color: #0f172a;
      display: block;
      font-size: 10px;
      margin-top: 2px;
    }}
    .finding {{
      background-color: #ffffff;
      border: 1px solid #cbd5e1;
      margin: 0;
      padding: 10px;
      page-break-inside: avoid;
    }}
    .finding-header {{
      border-collapse: collapse;
      margin-bottom: 8px;
      width: 100%;
    }}
    .finding-header td {{
      vertical-align: top;
    }}
    .severity {{
      color: #ffffff;
      font-size: 8px;
      font-weight: bold;
      padding: 5px 7px;
      text-align: center;
      width: 54px;
    }}
    .severity-icon {{
      height: 10px;
      width: 10px;
    }}
    .severity-critical {{ background: #991b1b; }}
    .severity-high {{ background: #dc2626; }}
    .severity-medium {{ background: #d97706; }}
    .severity-low {{ background: #2563eb; }}
    .severity-info {{ background: #475569; }}
    .remediation {{
      background: #f0fdf4;
      border-left: 3px solid #22c55e;
      margin-top: 8px;
      padding: 8px;
    }}
    .remediation h4,
    .remediation p {{
      color: #166534;
    }}
  </style>
</head>
<body bgcolor="#ffffff" style="background-color: #ffffff;">
<div class="page" style="background-color: #ffffff;">
  <table class="brand-table">
    <tr>
      <td class="brand-icon"><img src="{shield_icon}" alt=""></td>
      <td>
        <div class="eyebrow">SecuScan security export</div>
        <h1>{target_html}</h1>
      </td>
    </tr>
  </table>
  <p class="muted">Tool: {cls._escape_html(payload['tool_name'])} | Status: {cls._escape_html(payload['status'].upper())} | Exported: {cls._escape_html(payload['generated_at'])}</p>

  <table class="stats">
    <tr>
      <td><img class="stat-icon" src="{findings_icon}" alt=""><label>Total findings</label><strong>{len(findings)}</strong></td>
      <td><img class="stat-icon" src="{critical_icon}" alt=""><label>Critical</label><strong>{severity_counts['CRITICAL']}</strong></td>
      <td><img class="stat-icon" src="{target_icon}" alt=""><label>High</label><strong>{severity_counts['HIGH']}</strong></td>
      <td><img class="stat-icon" src="{rows_icon}" alt=""><label>Structured rows</label><strong>{len(payload['rows'])}</strong></td>
    </tr>
  </table>

  <h2><img class="stat-icon" src="{shield_icon}" alt=""> Executive Overview</h2>
  {f'''<div style="margin-bottom:12px;padding:10px 12px;background:#f0f4ff;border-left:4px solid #2563eb;border-radius:3px;"><strong style="display:block;margin-bottom:4px;font-size:9px;text-transform:uppercase;letter-spacing:.08em;color:#1e3a8a;">&#129302; AI Executive Summary</strong><p style="margin:0;font-size:9px;line-height:1.55;color:#1e293b;">{cls._escape_html(ai_summary)}</p></div>''' if ai_summary else ""}
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
</html>"""

    @classmethod
    def generate_pdf_report(cls, task: Dict[str, Any], result: Dict[str, Any]) -> bytes:
        """Generate the PDF from the same HTML used by the browser report.

        Contract:
            - Returns raw PDF bytes on success.
            - Raises RuntimeError("Failed to render SecuScan HTML report as PDF")
              on any render failure (pisa error flag or unexpected exception).
            - The internal BytesIO buffer is always closed before returning or
              raising, regardless of the failure mode.
            - No temporary files are written to disk; if this ever changes, the
              same try/finally guarantee must be preserved.
        """
        html_report = cls._generate_pdf_html_report(task, result)
        output = io.BytesIO()
        try:
            pdf = pisa.CreatePDF(src=html_report, dest=output, encoding="utf-8")
            if pdf.err:
                raise RuntimeError("Failed to render SecuScan HTML report as PDF")
            return output.getvalue()
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError("Failed to render SecuScan HTML report as PDF") from exc
        finally:
            output.close()

    @classmethod
    def generate_html_report(cls, task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generate a modern HTML report suitable for direct download."""
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
            f"""
            <article class="finding-card severity-{finding['severity'].lower()}">
                <div class="finding-top">
                    <span class="severity severity-{finding['severity'].lower()}"><img class="mini-icon" src="{critical_icon}" alt=""> {cls._escape_html(finding['severity'])}</span>
                    <div class="finding-heading">
                        <h3>{cls._escape_html(finding['title'])}</h3>
                        <p>{cls._escape_html(finding['category'])} | {cls._escape_html_with_breaks(finding['target'] or payload['target'])}</p>
                    </div>
                </div>
                <div class="finding-body">
                    <section>
                        <h4>Description</h4>
                        <p>{cls._escape_html(finding['description'])}</p>
                    </section>
                    {f"<section><h4>Evidence</h4><pre>{cls._escape_html(finding['proof'])}</pre></section>" if finding['proof'] else ""}
                    {f"<section class='meta'><span>Validated: {'YES' if finding['validated'] else 'NO'}</span></section>" if finding['validated'] or finding['validation_method'] else ""}
                    {f"<section class='meta'><span>Validation method: {cls._escape_html(finding['validation_method'])}</span></section>" if finding['validation_method'] else ""}
                    {f"<section class='meta'><span>CPE: {cls._escape_html(finding['cpe'])}</span></section>" if finding['cpe'] else ""}
                    {f"<section class='meta'><span>Evidence items: {len(finding['evidence'])}</span></section>" if finding['evidence'] else ""}
                    {f"<section class='remediation'><h4>Recommended action</h4><p>{cls._escape_html(finding['remediation'])}</p></section>" if finding['remediation'] else ""}
                    {f"<section class='meta'><span>CVE: {cls._escape_html(finding['cve'])}</span></section>" if finding['cve'] else ""}
                </div>
            </article>
            """
            for finding in findings
        )

        if not finding_markup:
            finding_markup = """
            <article class="finding-card empty-state">
                <div class="finding-body">
                    <h3>No structured findings were available</h3>
                    <p>This report finished without parsed findings. Review the raw task output in SecuScan for more detail.</p>
                </div>
            </article>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SecuScan Report - {cls._escape_html(payload['target'])}</title>
  <style>
    :root {{
      --ink: #0f172a;
      --muted: #475569;
      --subtle: #64748b;
      --panel: #ffffff;
      --panel-alt: #f8fafc;
      --line: #e2e8f0;
      --bg: linear-gradient(180deg, #e0f2fe 0%, #f8fafc 22%, #f8fafc 100%);
      --critical: #991b1b;
      --high: #dc2626;
      --medium: #d97706;
      --low: #2563eb;
      --info: #475569;
      --success-bg: #f0fdf4;
      --success-ink: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
      padding: 36px 18px 80px;
      line-height: 1.6;
    }}
    .shell {{ max-width: 1100px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 58%, #0f766e 100%);
      color: white;
      border-radius: 24px;
      padding: 32px;
      box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
    }}
    .hero-title {{
      align-items: flex-start;
      display: flex;
      gap: 16px;
    }}
    .hero-icon {{
      border: 1px solid rgba(255, 255, 255, 0.28);
      border-radius: 16px;
      height: 56px;
      padding: 8px;
      width: 56px;
    }}
    .hero-icon img, .card-icon img, .section-icon, .mini-icon {{
      display: block;
    }}
    .card-icon img {{
      height: 26px;
      width: 26px;
    }}
    .section-icon {{
      display: inline-block;
      height: 22px;
      margin-right: 8px;
      vertical-align: middle;
      width: 22px;
    }}
    .mini-icon {{
      display: inline-block;
      height: 14px;
      margin-right: 4px;
      vertical-align: middle;
      width: 14px;
    }}
    .eyebrow {{
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-size: 12px;
      opacity: 0.85;
      margin-bottom: 10px;
    }}
    h1 {{ margin: 0; font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.05; }}
    .hero p {{ max-width: 760px; color: rgba(255, 255, 255, 0.86); }}
    .meta-grid, .stat-grid {{
      display: grid;
      gap: 16px;
      margin-top: 24px;
    }}
    .meta-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .stat-grid {{ grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); margin-top: 28px; }}
    .meta-card, .stat-card, .finding-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 14px 40px rgba(15, 23, 42, 0.06);
    }}
    .meta-card, .stat-card {{ padding: 18px 20px; }}
    .meta-card label, .stat-card label {{
      display: block;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--subtle);
      margin-bottom: 8px;
      font-weight: 700;
    }}
    .meta-card strong, .stat-card strong {{
      font-size: 1.35rem;
      color: var(--ink);
    }}
    .stat-card {{
      position: relative;
      overflow: hidden;
    }}
    .stat-card-header {{
      align-items: center;
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
    }}
    .stat-card::before {{
      content: "";
      position: absolute;
      inset: 0 auto 0 0;
      width: 6px;
      background: var(--accent, var(--info));
    }}
    .section {{
      margin-top: 28px;
      background: rgba(255, 255, 255, 0.58);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(226, 232, 240, 0.9);
      border-radius: 24px;
      padding: 26px;
    }}
    .section h2 {{
      margin: 0 0 10px;
      font-size: 1.6rem;
    }}
    .section-copy {{
      margin: 0 0 18px;
      color: var(--muted);
    }}
    .summary-list {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
    }}
    .findings {{
      display: grid;
      gap: 18px;
    }}
    .finding-card {{
      overflow: hidden;
      border-left: 6px solid var(--info);
    }}
    .finding-card.severity-critical {{ border-left-color: var(--critical); }}
    .finding-card.severity-high {{ border-left-color: var(--high); }}
    .finding-card.severity-medium {{ border-left-color: var(--medium); }}
    .finding-card.severity-low {{ border-left-color: var(--low); }}
    .finding-card.severity-info {{ border-left-color: var(--info); }}

    .finding-card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
    }}
    .finding-top {{
      display: flex;
      gap: 16px;
      align-items: flex-start;
      padding: 20px 22px 14px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-alt);
    }}
    .finding-heading h3 {{
      margin: 0 0 4px;
      font-size: 1.2rem;
    }}
    .finding-heading p {{
      margin: 0;
      color: var(--subtle);
      font-size: 0.95rem;
    }}
    .severity {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 90px;
      padding: 7px 12px;
      border-radius: 999px;
      color: white;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .severity-critical {{ background: var(--critical); }}
    .severity-high {{ background: var(--high); }}
    .severity-medium {{ background: var(--medium); }}
    .severity-low {{ background: var(--low); }}
    .severity-info {{ background: var(--info); }}
    .finding-body {{
      padding: 22px;
      display: grid;
      gap: 16px;
    }}
    .finding-body h4 {{
      margin: 0 0 6px;
      font-size: 0.95rem;
    }}
    .finding-body p, .finding-body pre {{
      margin: 0;
      color: var(--muted);
    }}
    .finding-body pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #0f172a;
      color: #dbeafe;
      padding: 16px;
      border-radius: 14px;
      font-size: 0.9rem;
    }}
    .remediation {{
      background: var(--success-bg);
      border-left: 4px solid #22c55e;
      padding: 16px;
      border-radius: 14px;
    }}
    .remediation p, .remediation h4 {{ color: var(--success-ink); }}
    .empty-state {{ text-align: center; }}
    @page {{
      size: A4;
      margin: 14mm 12mm 16mm;
    }}
    @media print {{
      body {{
        background: white;
        padding: 0;
        print-color-adjust: exact;
      }}
      .shell {{ max-width: none; }}
      .hero {{
        box-shadow: none;
        break-inside: avoid;
      }}
      .meta-card,
      .stat-card,
      .finding-card {{
        break-inside: avoid;
      }}
      .finding-top {{
        break-after: avoid;
      }}
      .finding-body section {{
        break-inside: avoid;
      }}
      .section, .meta-card, .stat-card, .finding-card {{ box-shadow: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-title">
        <div class="hero-icon"><img src="{shield_icon}" alt=""></div>
        <div>
          <div class="eyebrow">SecuScan security export</div>
          <h1>{target_html}</h1>
          <p>This report packages the most important findings, evidence, and remediation guidance from the latest assessment run into a cleaner analyst-friendly format.</p>
        </div>
      </div>
    </section>

    <div class="meta-grid">
      <div class="meta-card"><div class="stat-card-header"><label>Tool</label><span class="card-icon"><img src="{target_icon}" alt=""></span></div><strong>{cls._escape_html(payload['tool_name'])}</strong></div>
      <div class="meta-card"><div class="stat-card-header"><label>Status</label><span class="card-icon"><img src="{shield_icon}" alt=""></span></div><strong>{cls._escape_html(payload['status'].upper())}</strong></div>
      <div class="meta-card"><div class="stat-card-header"><label>Task Started</label><span class="card-icon"><img src="{clock_icon}" alt=""></span></div><strong>{cls._escape_html(cls._format_timestamp(payload['created_at']))}</strong></div>
      <div class="meta-card"><div class="stat-card-header"><label>Exported</label><span class="card-icon"><img src="{rows_icon}" alt=""></span></div><strong>{cls._escape_html(payload['generated_at'])}</strong></div>
    </div>

    <div class="stat-grid">
      <div class="stat-card" style="--accent: #0f172a;"><div class="stat-card-header"><label>Total findings</label><span class="card-icon"><img src="{findings_icon}" alt=""></span></div><strong>{len(findings)}</strong></div>
      <div class="stat-card" style="--accent: #991b1b;"><div class="stat-card-header"><label>Critical</label><span class="card-icon"><img src="{critical_icon}" alt=""></span></div><strong>{severity_counts['CRITICAL']}</strong></div>
      <div class="stat-card" style="--accent: #dc2626;"><div class="stat-card-header"><label>High</label><span class="card-icon"><img src="{target_icon}" alt=""></span></div><strong>{severity_counts['HIGH']}</strong></div>
      <div class="stat-card" style="--accent: #2563eb;"><div class="stat-card-header"><label>Structured rows</label><span class="card-icon"><img src="{rows_icon}" alt=""></span></div><strong>{len(payload['rows'])}</strong></div>
    </div>

    <section class="section">
      <h2><img class="section-icon" src="{shield_icon}" alt="">Executive Overview</h2>
      <p class="section-copy">Key takeaways and severity distribution generated from the parsed assessment data.</p>
      <div class="executive-container" style="display: flex; gap: 24px; align-items: flex-start; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 300px;">
          {f'''<div style="margin:0 0 18px;padding:16px 20px;background:#eff6ff;border-left:4px solid #2563eb;border-radius:14px;"><p style="margin:0 0 6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#1d4ed8;">&#129302; AI Executive Summary</p><p style="margin:0;color:#1e293b;line-height:1.65;">{cls._escape_html(ai_summary)}</p></div>''' if ai_summary else ""}
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
</html>"""

    @classmethod
    def generate_csv_report(cls, task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generate a structured CSV export.

        Contract:
            - Returns a UTF-8 CSV string on success.
            - Raises RuntimeError on unexpected generation failure.
            - The internal StringIO buffer is always closed.
        """
        payload = cls._build_report_payload(task, result)
        output = io.StringIO()
        try:
            writer = csv.writer(output)
            writer.writerow(
                [
                    "Severity",
                    "Title",
                    "Category",
                    "Target",
                    "CVSS",
                    "CVE",
                    "CPE",
                    "Validated",
                    "Validation Method",
                    "Confidence Reason",
                    "Description",
                    "Evidence",
                    "Remediation",
                ]
            )
            for finding in payload["findings"]:
                writer.writerow(
                    [
                        finding["severity"],
                        finding["title"],
                        finding["category"],
                        finding["target"] or payload["target"],
                        finding["cvss"] if finding["cvss"] is not None else "",
                        finding["cve"],
                        finding["cpe"],
                        "yes" if finding["validated"] else "no",
                        finding["validation_method"],
                        finding["confidence_reason"],
                        finding["description"],
                        finding["proof"],
                        finding["remediation"],
                    ]
                )
            return output.getvalue()
        except Exception as exc:
            raise RuntimeError("Failed to generate CSV report") from exc
        finally:
            output.close()

    @classmethod
    def generate_sarif_report(cls, task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generate a SARIF v2.1.0 report for GitHub Code Scanning."""
        payload = cls._build_report_payload(task, result)
        tool_name = payload["tool_name"]

        # Define severity mapping to SARIF levels
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
            # Check if target looks like a file path or URI
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
