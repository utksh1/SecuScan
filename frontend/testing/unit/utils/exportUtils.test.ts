import { describe, test, expect, vi, beforeEach, afterEach } from "vitest";
import { downloadBlob, downloadFile, findingsExportFilename } from "../../../src/utils/exportUtils";

// The CSV/JSON serializers that used to live here moved to the backend with
// issue #1875 — the browser no longer builds export files, it downloads them.
// Their column contract is now pinned by testing/backend/unit/test_finding_export.py.

describe("exportUtils utility", () => {
  let createObjectURL: ReturnType<typeof vi.fn>;
  let revokeObjectURL: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    createObjectURL = vi.fn(() => "blob:mock-url");
    revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("downloadBlob triggers a download and releases the object URL", () => {
    const click = vi.fn();
    const anchor = document.createElement("a");
    anchor.click = click;
    vi.spyOn(document, "createElement").mockReturnValueOnce(anchor);

    downloadBlob(new Blob(["payload"]), "findings.csv");

    expect(anchor.download).toBe("findings.csv");
    expect(anchor.href).toBe("blob:mock-url");
    expect(click).toHaveBeenCalledOnce();
    // Leaving the URL alive would leak the blob for the lifetime of the document.
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
    expect(document.body.contains(anchor)).toBe(false);
  });

  test("downloadFile wraps its content in a blob of the given type", () => {
    vi.spyOn(document, "createElement").mockReturnValueOnce(
      Object.assign(document.createElement("a"), { click: vi.fn() }),
    );

    downloadFile("a,b,c", "findings.csv", "text/csv");

    const blob = createObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe("text/csv");
  });

  test("findingsExportFilename is dated and carries the format extension", () => {
    const when = new Date("2026-05-12T10:30:00Z");
    expect(findingsExportFilename("csv", when)).toBe("secuscan_findings_2026-05-12.csv");
    expect(findingsExportFilename("sarif", when)).toBe("secuscan_findings_2026-05-12.sarif");
  });
});
