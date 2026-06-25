import { render, screen } from "@testing-library/react";
import { ExecutiveStatsBar } from "../../../src/components/ExecutiveStatsBar";

describe("ExecutiveStatsBar", () => {
  const defaultProps = {
    riskLabel: "Moderate",
    criticalVulns: 3,
    totalFindings: 42,
    scanActivity: 7,
    compliancePercent: 88,
    riskNote: "Test risk note",
  };

  // Non-loading state — actual data renders
  it("renders risk label, vuln counts, and findings when not loading", () => {
    render(<ExecutiveStatsBar {...defaultProps} loading={false} />);
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("Test risk note")).toBeInTheDocument();
  });

  it("does not render loading skeleton status roles when not loading", () => {
    render(<ExecutiveStatsBar {...defaultProps} loading={false} />);
    expect(screen.queryAllByRole("status")).toHaveLength(0);
  });

  it("marks the container aria-busy false when not loading", () => {
    const { container } = render(<ExecutiveStatsBar {...defaultProps} loading={false} />);
    expect(container.firstChild).toHaveAttribute("aria-busy", "false");
  });

  // Loading state — skeletons render instead of data
  it("renders skeleton placeholders when loading", () => {
    render(<ExecutiveStatsBar {...defaultProps} loading={true} />);
    // Card 1 has 3 skeleton blocks (heading + 2 text lines), cards 2-4 have 2 each = 9 total
    expect(screen.getAllByRole("status")).toHaveLength(9);
  });

  it("does not render actual metric values when loading", () => {
    render(<ExecutiveStatsBar {...defaultProps} loading={true} riskLabel="Moderate" />);
    expect(screen.queryByText("Moderate")).not.toBeInTheDocument();
    expect(screen.queryByText("3")).not.toBeInTheDocument();
    expect(screen.queryByText("42")).not.toBeInTheDocument();
    expect(screen.queryByText("Test risk note")).not.toBeInTheDocument();
  });

  it("marks the container aria-busy true when loading", () => {
    const { container } = render(<ExecutiveStatsBar {...defaultProps} loading={true} />);
    expect(container.firstChild).toHaveAttribute("aria-busy", "true");
  });

  it("still renders the four section headers when loading", () => {
    render(<ExecutiveStatsBar {...defaultProps} loading={true} />);
    expect(screen.getByText("Status Profile")).toBeInTheDocument();
    expect(screen.getByText("Critical Vulns")).toBeInTheDocument();
    expect(screen.getByText("Total Findings")).toBeInTheDocument();
    expect(screen.getByText("Scan Cycles")).toBeInTheDocument();
  });

  // Default loading is false when prop omitted
  it("defaults to non-loading state when loading prop is omitted", () => {
    render(<ExecutiveStatsBar {...defaultProps} />);
    expect(screen.getByText("Moderate")).toBeInTheDocument();
    expect(screen.queryAllByRole("status")).toHaveLength(0);
  });
});
