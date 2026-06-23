import { describe, test, expect } from "vitest";
import { generateMarkdownReport, Summary } from "../../../src/utils/reportBuilder";

describe("reportBuilder utility", () => {
  const sampleSummary: Summary = {
    total_findings: 5,
    critical_findings: 1,
    high_findings: 2,
    medium_findings: 1,
    low_findings: 1,
    info_findings: 0,
    last_scan_time: "2026-05-12T10:30:00Z",
    recent_findings: [
      {
        id: "f1",
        severity: "critical",
        title: "SQL Injection",
        target: "http://target1.local",
        discovered_at: "2026-05-12T10:30:00Z"
      },
      {
        id: "f2",
        severity: "high",
        title: "Cross-Site Scripting",
        target: "http://target2.local",
        discovered_at: "2026-05-12T10:35:00Z"
      }
    ],
    running_tasks: [],
    recent_tasks: [
      {
        id: "t1",
        plugin_id: "sqlmap",
        tool_name: "SQLMap Scanner",
        target: "http://target1.local",
        status: "completed",
        created_at: "2026-05-12T10:29:00Z",
        duration_seconds: 45
      }
    ],
    scan_activity: {
      total: 10,
      completed: 9,
      running: 1
    }
  };

  test("generates correct report structure under threat condition", () => {
    const report = generateMarkdownReport(sampleSummary, "Severe");

    // Header checks
    expect(report).toContain("# SecuScan Security Audit Report");
    expect(report).toContain("Overall Threat Level:** SEVERE");

    // Executive summary checks
    expect(report).toContain("| Metric | Count |");
    expect(report).toContain("| Critical Risk | 1 |");
    expect(report).toContain("| High Severity | 2 |");

    // Scan activity details
    expect(report).toContain("**Total Tasks Executed:** 10");
    expect(report).toContain("**Completed Tasks:** 9");
    expect(report).toContain("**Active/Running Tasks:** 1");

    // Recent findings checks
    expect(report).toContain("| Title | Severity | Target | Discovered At |");
    expect(report).toContain("| SQL Injection | **CRITICAL** | `http://target1.local` |");

    // Task activity checks
    expect(report).toContain("| Tool/Plugin | Target | Status | Created At | Duration |");
    expect(report).toContain("| SQLMAP SCANNER | `http://target1.local` | COMPLETED |");

    // Remediation Roadmap checks
    expect(report).toContain("### High Priority Action Items");
    expect(report).toContain("**Critical Alert:** Address the 1 critical vulnerability/vulnerabilities immediately");
    expect(report).toContain("**High Alert:** Review and remediate the 2 high-severity issue(s)");
  });

  test("handles empty lists gracefully", () => {
    const emptySummary: Summary = {
      total_findings: 0,
      critical_findings: 0,
      high_findings: 0,
      medium_findings: 0,
      low_findings: 0,
      info_findings: 0,
      last_scan_time: null,
      recent_findings: [],
      running_tasks: [],
      recent_tasks: [],
      scan_activity: {
        total: 0,
        completed: 0,
        running: 0
      }
    };

    const report = generateMarkdownReport(emptySummary, "Stable");

    expect(report).toContain("Overall Threat Level:** STABLE");
    expect(report).toContain("No recent findings detected.");
    expect(report).toContain("No recent task activity logged.");
    expect(report).toContain("No critical or high severity vulnerabilities found. Continue regular scanning cycles to maintain security posture.");
  });
});
