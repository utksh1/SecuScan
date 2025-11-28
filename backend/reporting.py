import csv
import io
import json
from io import BytesIO
from fpdf import FPDF
from typing import Dict, Any

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
        writer.writerow(['Task ID', 'Tool', 'Target', 'Created At'])
        writer.writerow([task.get('id', ''), task.get('tool_name', ''), task.get('target', ''), task.get('created_at', '')])
        writer.writerow([])

        # Write Findings header
        writer.writerow(['Severity', 'Title', 'Description'])

        # Write Findings
        structured_data = result.get('structured', {})
        findings = structured_data.get('findings', [])

        if findings:
            for finding in findings:
                writer.writerow([
                    finding.get('severity', 'info'),
                    finding.get('title', ''),
                    finding.get('description', '')
                ])
        else:
            writer.writerow(['No structured findings found.'])

        return output.getvalue()

    @staticmethod
    def generate_pdf_report(task: Dict[str, Any], result: Dict[str, Any]) -> bytes:
        """
        Generate a PDF byte string from task results.
        """
        pdf = FPDF()
        pdf.add_page()

        # Title
        pdf.set_font("helvetica", "B", 20)
        pdf.cell(0, 10, "SecuScan - Vulnerability Report", new_x="LMARGIN", new_y="NEXT", align='C')
        pdf.ln(10)

        # Metadata
        pdf.set_font("helvetica", "B", 12)
        pdf.cell(40, 10, "Task ID:", border=0)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, str(task.get('id', '')), border=0, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 12)
        pdf.cell(40, 10, "Tool:", border=0)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, str(task.get('tool_name', '')), border=0, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 12)
        pdf.cell(40, 10, "Target:", border=0)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, str(task.get('target', '')), border=0, new_x="LMARGIN", new_y="NEXT")

        pdf.set_font("helvetica", "B", 12)
        pdf.cell(40, 10, "Date:", border=0)
        pdf.set_font("helvetica", "", 12)
        pdf.cell(0, 10, str(task.get('created_at', '')), border=0, new_x="LMARGIN", new_y="NEXT")

        pdf.ln(10)

        # Summary
        summary = result.get('summary', [])
        if summary:
            pdf.set_font("helvetica", "B", 16)
            pdf.cell(0, 10, "Summary", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            pdf.set_font("helvetica", "", 12)
            for item in summary:
                pdf.multi_cell(0, 8, f"- {item}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(10)

        # Findings
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "Findings", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        structured_data = result.get('structured', {})
        findings = structured_data.get('findings', [])

        if findings:
            for finding in findings:
                # Severity Badge Simulation
                pdf.set_font("helvetica", "B", 12)
                severity = finding.get('severity', 'info').upper()
                title = finding.get('title', 'Unknown Issue')

                pdf.set_text_color(255, 0, 0) if severity in ['CRITICAL', 'HIGH'] else (
                    pdf.set_text_color(200, 150, 0) if severity == 'MEDIUM' else pdf.set_text_color(0, 150, 0)
                )

                pdf.cell(30, 8, f"[{severity}]")
                pdf.set_text_color(0, 0, 0)
                pdf.multi_cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")

                description = finding.get('description', '')
                if description:
                    pdf.set_font("helvetica", "", 11)
                    pdf.multi_cell(0, 6, description, new_x="LMARGIN", new_y="NEXT")

                pdf.ln(4)
        else:
            pdf.set_font("helvetica", "I", 12)
            pdf.cell(0, 10, "No structured findings reported.", new_x="LMARGIN", new_y="NEXT")

        return pdf.output()

reporting = ReportGenerator()
