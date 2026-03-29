import csv
import io
import json
import os
import re
from io import BytesIO
from fpdf import FPDF
from typing import Dict, Any, List, Optional
from datetime import datetime

class SecuScanPDF(FPDF):
    """Custom FPDF class for SecuScan reports."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo.png")
        self.brand_color = (43, 108, 176) # Professional Blue

    def header(self):
        # Draw background header bar on first page
        if self.page_no() == 1:
            self.set_fill_color(248, 250, 252)
            self.rect(0, 0, 210, 40, "F")
            
        # Logo
        if os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 10, 30)
        
        # Title
        self.set_font("helvetica", "B", 16)
        self.set_text_color(*self.brand_color)
        self.cell(80)
        self.cell(30, 20, "SECUSCAN SECURITY AUDIT", border=0, align="C")
        self.ln(25)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f"SecuScan Vulnerability Report - Page {self.page_no()}/{{nb}}", align="C")
        self.set_x(-45)
        self.cell(35, 10, datetime.now().strftime("%Y-%m-%d %H:%M"), align="R")

class ReportGenerator:
    """Handles professional PDF, HTML, and CSV generation for security audits."""

    ANSI_ESCAPE_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0B-\x1F\x7F]')
    
    SEVERITY_COLORS = {
        'CRITICAL': (153, 27, 27), # Dark Red
        'HIGH': (220, 38, 38),     # Red
        'MEDIUM': (217, 119, 6),   # Amber
        'LOW': (37, 99, 235),      # Blue
        'INFO': (100, 116, 139)    # Slate
    }

    @classmethod
    def _clean_text(cls, value: Any) -> str:
        if value is None: return ""
        text = str(value)
        text = cls.ANSI_ESCAPE_RE.sub('', text)
        text = cls.CONTROL_CHARS_RE.sub('', text)
        return text.strip()

    @staticmethod
    def generate_pdf_report(task: Dict[str, Any], result: Dict[str, Any]) -> bytes:
        """Generates a high-fidelity PDF report."""
        pdf = SecuScanPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        
        findings = result.get('findings', [])
        summary = result.get('summary', [])
        target = task.get('target', 'Unknown')
        
        # 1. Executive Summary
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, "1. Executive Summary", ln=True)
        pdf.ln(2)
        
        pdf.set_font("helvetica", "", 10)
        pdf.multi_cell(0, 6, f"This security audit was performed on {target} using {task.get('tool_name')}. "
                             f"The assessment identified {len(findings)} findings.")
        pdf.ln(5)

        # 2. Risk Distribution
        severity_counts = {}
        for f in findings:
            sev = f.get('severity', 'info').upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if severity_counts:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Risk Profile", ln=True)
            for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
                count = severity_counts.get(sev, 0)
                if count > 0:
                    color = ReportGenerator.SEVERITY_COLORS.get(sev, (100, 100, 100))
                    pdf.set_fill_color(*color)
                    pdf.rect(10, pdf.get_y()+2, count * 5, 4, 'F')
                    pdf.set_x(count * 5 + 15)
                    pdf.set_font("helvetica", "B", 9)
                    pdf.set_text_color(*color)
                    pdf.cell(0, 8, f"{sev}: {count}")
                    pdf.ln(6)
            pdf.ln(10)

        # 3. Detailed Technical Findings
        pdf.add_page()
        pdf.set_font("helvetica", "B", 14)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, "2. Technical Findings", ln=True)
        pdf.ln(5)

        for idx, finding in enumerate(findings):
            # Page break if near bottom
            if pdf.get_y() > 240: pdf.add_page()
            
            sev = finding.get('severity', 'info').upper()
            color = ReportGenerator.SEVERITY_COLORS.get(sev, (100, 100, 100))
            
            # Finding Header
            pdf.set_fill_color(*color)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("helvetica", "B", 10)
            pdf.cell(25, 8, f" {sev} ", fill=True)
            pdf.set_fill_color(248, 250, 252)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(0, 8, f"  Finding #{idx+1}: {finding.get('title')}", fill=True, ln=True)
            
            # Details
            pdf.ln(2)
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(30, 6, "Category:")
            pdf.set_font("helvetica", "", 9)
            pdf.cell(0, 6, finding.get('category', 'General'), ln=True)
            
            pdf.set_font("helvetica", "B", 9)
            pdf.cell(0, 6, "Description:", ln=True)
            pdf.set_font("helvetica", "", 9)
            pdf.multi_cell(0, 5, ReportGenerator._clean_text(finding.get('description')))
            
            if remediation := finding.get('remediation'):
                pdf.ln(1)
                pdf.set_font("helvetica", "B", 9)
                pdf.set_text_color(22, 101, 52) # Dark Green
                pdf.cell(0, 6, "Remediation Recommendation:", ln=True)
                pdf.set_font("helvetica", "I", 9)
                pdf.multi_cell(0, 5, ReportGenerator._clean_text(remediation))
                pdf.set_text_color(0, 0, 0)

            pdf.ln(5)
            pdf.set_draw_color(226, 232, 240)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

        return bytes(pdf.output())

    @staticmethod
    def generate_html_report(task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generates a modern, responsive HTML report."""
        findings = result.get('findings', [])
        target = task.get('target', 'Unknown')
        
        # Generate summary stats
        stats = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}
        for f in findings:
            sev = f.get('severity', 'info').upper()
            stats[sev] = stats.get(sev, 0) + 1

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SecuScan Audit Report - {target}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #2563eb; --critical: #dc2626; --high: #ea580c; --medium: #f59e0b; --low: #3b82f6; --info: #64748b;
            --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --text-muted: #64748b;
        }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); line-height: 1.5; margin: 0; padding: 40px 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; }}
        header {{ margin-bottom: 40px; border-bottom: 2px solid #e2e8f0; padding-bottom: 20px; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; margin-bottom: 40px; }}
        .stat-card {{ background: var(--card); padding: 16px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; border-bottom: 4px solid var(--info); }}
        .stat-card.CRITICAL {{ border-color: var(--critical); }}
        .stat-card.HIGH {{ border-color: var(--high); }}
        .stat-card.MEDIUM {{ border-color: var(--medium); }}
        .stat-card.LOW {{ border-color: var(--low); }}
        .finding-card {{ background: var(--card); border-radius: 12px; margin-bottom: 24px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .finding-header {{ padding: 16px 20px; display: flex; align-items: center; gap: 12px; background: #f1f5f9; }}
        .badge {{ padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 12px; color: white; }}
        .badge.CRITICAL {{ background: var(--critical); }}
        .badge.HIGH {{ background: var(--high); }}
        .badge.MEDIUM {{ background: var(--medium); }}
        .badge.LOW {{ background: var(--low); }}
        .badge.INFO {{ background: var(--info); }}
        .content {{ padding: 20px; }}
        .remediation {{ background: #f0fdf4; border-left: 4px solid #16a34a; padding: 16px; margin-top: 16px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Security Audit Report</h1>
            <p style="color: var(--text-muted)">Target: <strong>{target}</strong> | Generated: {datetime.now().strftime("%B %d, %Y")}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card CRITICAL"><h3>{stats['CRITICAL']}</h3><p>Critical</p></div>
            <div class="stat-card HIGH"><h3>{stats['HIGH']}</h3><p>High</p></div>
            <div class="stat-card MEDIUM"><h3>{stats['MEDIUM']}</h3><p>Medium</p></div>
            <div class="stat-card LOW"><h3>{stats['LOW']}</h3><p>Low</p></div>
            <div class="stat-card INFO"><h3>{stats['INFO']}</h3><p>Info</p></div>
        </div>

        <h2>Vulnerability Details</h2>
        {"".join([f'''
        <div class="finding-card">
            <div class="finding-header">
                <span class="badge {f['severity'].upper()}">{f['severity'].upper()}</span>
                <strong>{f.get('title')}</strong>
            </div>
            <div class="content">
                <p><strong>Category:</strong> {f.get('category', 'General')}</p>
                <p>{f.get('description')}</p>
                {f'<div class="remediation"><strong>Recommendation:</strong><br>{f.get("remediation")}</div>' if f.get("remediation") else ""}
            </div>
        </div>
        ''' for f in findings])}
    </div>
</body>
</html>
        """
        return html

    @staticmethod
    def generate_csv_report(task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Generates a standard CSV report."""
        output = io.StringIO()
        writer = csv.writer(output)
        findings = result.get('findings', [])
        writer.writerow(['Severity', 'Title', 'Category', 'Description', 'Remediation'])
        for f in findings:
            writer.writerow([
                f.get('severity', 'info').upper(),
                f.get('title', ''),
                f.get('category', 'General'),
                f.get('description', ''),
                f.get('remediation', '')
            ])
        return output.getvalue()

reporting = ReportGenerator()
