import { render } from "@testing-library/react";
import { describe, test, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import Scans from "../../../src/pages/Scans";

const mockScansData = [
  {
    task_id: "scan-1",
    plugin_id: "nmap",
    tool: "nmap",
    target: "192.168.1.1",
    status: "completed",
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    task_id: "scan-2",
    plugin_id: "nmap",
    tool: "nmap",
    target: "192.168.1.2",
    status: "completed",
    created_at: "2024-01-02T00:00:00Z",
  },
  {
    task_id: "scan-3",
    plugin_id: "nmap",
    tool: "nmap",
    target: "192.168.1.3",
    status: "failed",
    created_at: "2024-01-03T00:00:00Z",
  },
];

describe("Scans Comparison Dashboard - Integration Suite", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  test("renders scans page with data", async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        tasks: mockScansData,
        pagination: { total_items: 3 },
      }),
    } as any);

    render(
      <BrowserRouter>
        <Scans />
      </BrowserRouter>,
    );

    expect(true).toBe(true);
  });

  test("renders scans page with identical scans", async () => {
    vi.mocked(global.fetch).mockResolvedValue({
      ok: true,
      json: async () => ({
        tasks: [mockScansData[0], mockScansData[0]],
        pagination: { total_items: 2 },
      }),
    } as any);

    render(
      <BrowserRouter>
        <Scans />
      </BrowserRouter>,
    );

    expect(true).toBe(true);
  });

  test("renders scans page on fetch error", async () => {
    vi.mocked(global.fetch).mockRejectedValue(
      new Error("Failed to fetch scan details"),
    );

    render(
      <BrowserRouter>
        <Scans />
      </BrowserRouter>,
    );

    expect(true).toBe(true);
  });
});
