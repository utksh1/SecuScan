import csv
import io
import json
import os
from io import BytesIO
from fpdf import FPDF
from typing import Dict, Any, List
from datetime import datetime

class SecuScanPDF(FPDF):
    """Custom FPDF class for SecuScan reports."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "logo.png")

    def header(self):
        # Logo
        if os.path.exists(self.logo_path):
            self.image(self.logo_path, 10, 8, 33)
        
        # Title
        self.set_font("helvetica", "B", 15)
        self.cell(80)
        self.cell(30, 10, "SecuScan Security Report", border=0, align="C")
        self.ln(20)

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        # helvetica italic 8
        self.set_font("helvetica", "I", 8)
        # Page number
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")
        # Date on the right
        self.set_x(-40)
        self.cell(30, 10, datetime.now().strftime("%Y-%m-%d"), align="R")

class ReportGenerator:
    """Handles PDF and CSV generation for task results."""

    @staticmethod
    def generate_csv_report(task: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Generate a CSV string from task findings.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(['Task ID', 'Tool', 'Target', 'Created At', 'Status'])
        writer.writerow([
            task.get('id', ''), 
            task.get('tool_name', ''), 
            task.get('target', ''), 
            task.get('created_at', ''),
            result.get('status', 'completed')
        ])
        writer.writerow([])

        # Write Findings header
        writer.writerow(['Severity', 'Title', 'Description', 'Remediation'])

        # Write Findings
        structured_data = result.get('structured', {})
        if findings := structured_data.get('findings', []):
            for finding in findings:
                writer.writerow([
                    finding.get('severity', 'info').upper(),
                    finding.get('title', ''),
                    finding.get('description', ''),
                    finding.get('remediation', '')
                ])
        else:
            writer.writerow(['No structured findings found.'])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(task: Dict[str, Any], result: Dict[str, Any]) -> bytes:
        """
        Generate a professional PDF report from task results.
        """
        pdf = SecuScanPDF()
        pdf.alias_nb_pages()
        pdf.add_page()

        # Severity Colors Mapping
        colors = {
            'CRITICAL': (255, 0, 0),
            'HIGH': (255, 69, 0),
            'MEDIUM': (255, 165, 0),
            'LOW': (255, 215, 0),
            'INFO': (135, 206, 235)
        }

        # 1. Executive Summary
        pdf.set_font("helvetica", "B", 16)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 12, "Executive Summary", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(4)

        # Overview Table
        pdf.set_font("helvetica", "B", 10)
        pdf.set_fill_color(200, 200, 200)
        col_width = pdf.epw / 4
        pdf.cell(col_width, 8, "Task ID", border=1, fill=True)
        pdf.cell(col_width, 8, "Tool", border=1, fill=True)
        pdf.cell(col_width, 8, "Target", border=1, fill=True)
        pdf.cell(col_width, 8, "Status", border=1, fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", 10)
        pdf.cell(col_width, 8, str(task.get('id', '')[:8]), border=1)
        pdf.cell(col_width, 8, str(task.get('tool_name', '')), border=1)
        pdf.cell(col_width, 8, str(task.get('target', '')), border=1)
        pdf.cell(col_width, 8, str(result.get('status', 'completed')), border=1)
        pdf.ln(10)

        # Severity Summary Counts
        severity_counts = result.get('severity_counts', {})
        if severity_counts:
            pdf.set_font("helvetica", "B", 12)
            pdf.cell(0, 10, "Findings by Severity", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
            for sev, count in severity_counts.items():
                if count > 0:
                    pdf.set_font("helvetica", "B", 10)
                    color = colors.get(sev.upper(), (200, 200, 200))
                    pdf.set_text_color(*color)
                    pdf.cell(30, 8, f"{sev.upper()}:")
                    pdf.set_text_color(0, 0, 0)
                    pdf.set_font("helvetica", "", 10)
                    pdf.cell(20, 8, str(count))
                    
                    # Small bar
                    pdf.set_fill_color(*color)
                    pdf.rect(pdf.get_x(), pdf.get_y() + 2, count * 5, 4, 'F')
                    pdf.ln(8)
            pdf.ln(10)

        # 2. Key Observations (Summary)
        if summary := result.get('summary', []):
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "Key Observations", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_font("helvetica", "", 11)
            for item in summary:
                # Bullet point simulation
                pdf.set_font("helvetica", "B", 12)
                pdf.cell(5, 7, chr(149)) # Bullet character
                pdf.set_font("helvetica", "", 11)
                pdf.multi_cell(0, 7, item, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)

        # 3. Detailed Findings
        pdf.set_font("helvetica", "B", 16)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 12, "Detailed Findings", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(5)

        structured_data = result.get('structured', {})
        findings = structured_data.get('findings', [])
        
        if findings:
            for idx, finding in enumerate(findings):
                severity = finding.get('severity', 'info').upper()
                title = finding.get('title', 'Unknown Issue')
                
                # Check for page break
                if pdf.get_y() > 250:
                    pdf.add_page()

                # Finding Header
                pdf.set_font("helvetica", "B", 12)
                color = colors.get(severity, (0, 0, 0))
                pdf.set_fill_color(*color)
                pdf.set_text_color(255, 255, 255)
                pdf.cell(30, 8, f" {severity} ", new_x="RIGHT", fill=True)
                
                pdf.set_text_color(0, 0, 0)
                pdf.set_fill_color(245, 245, 245)
                pdf.cell(0, 8, f" Finding #{idx+1}: {title}", new_x="LMARGIN", new_y="NEXT", fill=True)
                pdf.ln(2)

                # Description
                if description := finding.get('description', ''):
                    pdf.set_font("helvetica", "B", 10)
                    pdf.cell(0, 7, "Description:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("helvetica", "", 10)
                    pdf.multi_cell(0, 6, description, new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)

                # Remediation (if available)
                if remediation := finding.get('remediation', ''):
                    pdf.set_font("helvetica", "B", 10)
                    pdf.cell(0, 7, "Remediation:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("helvetica", "I", 10)
                    pdf.multi_cell(0, 6, remediation, new_x="LMARGIN", new_y="NEXT")
                    pdf.ln(2)

                pdf.ln(4)
                pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.epw, pdf.get_y())
                pdf.ln(6)
        else:
            pdf.set_font("helvetica", "I", 12)
            pdf.cell(0, 10, "No structured findings reported for this task.", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()

reporting = ReportGenerator()
