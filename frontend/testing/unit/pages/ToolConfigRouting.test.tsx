import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ToolConfig from "../../../src/pages/ToolConfig";
import { routes } from "../../../src/routes";
import { getPluginSchema, listPlugins } from "../../../src/api";

vi.mock("../../../src/components/ToastContext", () => ({
  useToast: () => ({ addToast: vi.fn() }),
}));

vi.mock("../../../src/api", () => ({
  listPlugins: vi.fn(),
  getPluginSchema: vi.fn(),
  startTask: vi.fn(),
}));

function renderWithRoutes(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path={routes.scanTool} element={<ToolConfig />} />
        <Route
          path={routes.scans}
          element={<div data-testid="scans-page">SCANS</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe("ToolConfig route consistency", () => {
  beforeEach(() => {
    vi.mocked(listPlugins).mockResolvedValue({
      total: 1,
      plugins: [
        {
          id: "whois_lookup",
          name: "WHOIS Lookup",
          description: "Domain registration information",
          category: "recon",
          safety_level: "safe",
          enabled: true,
          icon: "🔎",
          requires_consent: false,
          consent_message: null,
          availability: { runnable: true, missing_binaries: [] },
        },
      ],
    });
    vi.mocked(getPluginSchema).mockResolvedValue({
      id: "whois_lookup",
      name: "WHOIS Lookup",
      description: "Domain registration information",
      fields: [
        { id: "target", label: "Domain", type: "string", required: true },
      ],
      presets: { default: {} },
      safety: { level: "safe", requires_consent: false },
    });
  });

  it("redirects unknown tool ids to /scans", async () => {
    renderWithRoutes("/toolkit/unknown-tool");

    await waitFor(() => {
      expect(screen.getByTestId("scans-page")).toBeInTheDocument();
    });
  });

  it("uses /scans for the back button destination", async () => {
    const user = userEvent.setup();
    renderWithRoutes("/toolkit/whois_lookup");

    const backButton = await screen.findByRole("button", {
      name: /arrow_back/i,
    });
    await user.click(backButton);

    await waitFor(() => {
      expect(screen.getByTestId("scans-page")).toBeInTheDocument();
    });
  });
});
