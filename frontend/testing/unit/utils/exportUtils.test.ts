import { describe, test, expect } from "vitest";
import { escapeCSV, serializeFindingsToCSV } from "../../../src/utils/exportUtils";

describe("exportUtils utility", () => {
  test("escapeCSV handles standard inputs", () => {
    expect(escapeCSV("hello")).toBe("hello");
    expect(escapeCSV(123)).toBe("123");
    expect(escapeCSV(null)).toBe("");
    expect(escapeCSV(undefined)).toBe("");
  });

  test("escapeCSV escapes quotes, commas, and newlines", () => {
    expect(escapeCSV('hello, world')).toBe('"hello, world"');
    expect(escapeCSV('hello "world"')).toBe('"hello ""world"""');
    expect(escapeCSV('hello\nworld')).toBe('"hello\nworld"');
  });

  test("serializeFindingsToCSV generates correct headers and mapped rows", () => {
    const sampleFindings = [
      {
        id: "f-1",
        title: "SQL Injection",
        severity: "critical",
        category: "Database",
        target: "http://target1.local",
        discovered_at: "2026-05-12T10:30:00Z",
        cvss: 9.8,
        cve: "CVE-2026-1234",
        risk_score: 9.5,
        confidence: 0.9,
        validated: true,
        analyst_status: "confirmed",
        description: "An injection vulnerability in input parameter.",
        remediation: "Use parameterized queries."
      },
      {
        id: "f-2",
        title: "Information Disclosure, Version Leak",
        severity: "info",
        category: "Information",
        target: "http://target2.local",
        discovered_at: "2026-05-12T10:35:00Z",
        cvss: null,
        cve: undefined,
        risk_score: 1.0,
        confidence: 1.0,
        validated: false,
        analyst_status: "new",
        description: "Version string \"1.2.3\" disclosed.",
        remediation: "Disable version banners."
      }
    ];

    const csvContent = serializeFindingsToCSV(sampleFindings);
    
    // Header check
    expect(csvContent).toContain("ID,Title,Severity,Category,Target,Discovered At,CVSS,CVE,Risk Score,Confidence,Validated,Analyst Status,Description,Remediation");
    
    // Row checks
    expect(csvContent).toContain("f-1,SQL Injection,critical,Database,http://target1.local,2026-05-12T10:30:00Z,9.8,CVE-2026-1234,9.5,0.9,true,confirmed,An injection vulnerability in input parameter.,Use parameterized queries.");
    
    // Check comma escaping in title, quote escaping in description
    expect(csvContent).toContain('"Information Disclosure, Version Leak"');
    expect(csvContent).toContain('"Version string ""1.2.3"" disclosed."');
  });
});
