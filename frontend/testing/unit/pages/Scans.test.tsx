import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

vi.mock("../../../src/api", () => ({
  API_BASE: "http://localhost:8000",
  deleteTask: vi.fn(),
  clearAllTasks: vi.fn(),
  bulkDeleteTasks: vi.fn().mockResolvedValue({}),
}));

global.fetch = vi.fn().mockResolvedValue({
  json: () =>
    Promise.resolve({
      tasks: [
        {
          task_id: "1",
          tool: "nmap",
          target: "localhost",
          status: "completed",
          created_at: new Date().toISOString(),
          plugin_id: "nmap",
        },
        {
          task_id: "2",
          tool: "nikto",
          target: "localhost",
          status: "completed",
          created_at: new Date().toISOString(),
          plugin_id: "nikto",
        },
      ],
      pagination: { total_items: 2 },
    }),
});

import Scans from "../../../src/pages/Scans";
import { bulkDeleteTasks } from "../../../src/api";

const renderScans = () =>
  render(
    <MemoryRouter>
      <Scans />
    </MemoryRouter>,
  );

describe("Scans bulk delete end-to-end flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn().mockResolvedValue({
      json: () =>
        Promise.resolve({
          tasks: [
            {
              task_id: "1",
              tool: "nmap",
              target: "localhost",
              status: "completed",
              created_at: new Date().toISOString(),
              plugin_id: "nmap",
            },
            {
              task_id: "2",
              tool: "nikto",
              target: "localhost",
              status: "completed",
              created_at: new Date().toISOString(),
              plugin_id: "nikto",
            },
          ],
          pagination: { total_items: 2 },
        }),
    });
  });

  it("does NOT call bulkDeleteTasks before confirmation", async () => {
    renderScans();
    expect(bulkDeleteTasks).not.toHaveBeenCalled();
  });

  it("modal is not visible on initial render", async () => {
    renderScans();
    expect(
      screen.queryByRole("dialog", { hidden: true }),
    ).not.toBeInTheDocument();
  });

  it("no deletion happens without user confirmation", async () => {
    renderScans();
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(bulkDeleteTasks).not.toHaveBeenCalled();
  });
});
