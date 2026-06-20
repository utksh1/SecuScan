import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import { ToolCheatSheet } from "../../src/components/ToolCheatSheet/ToolCheatSheet";

function renderPanel(activeToolId: string) {
  return render(<ToolCheatSheet activeToolId={activeToolId} />);
}

function getTrigger() {
  return screen.getByRole("button", { name: /learning center/i });
}

describe("ToolCheatSheet — open/close", () => {
  it("renders closed by default", () => {
    renderPanel("nmap");
    expect(screen.queryByTestId("learning-panel-content")).not.toBeInTheDocument();
  });

  it("has aria-expanded=false when closed", () => {
    renderPanel("nmap");
    expect(getTrigger()).toHaveAttribute("aria-expanded", "false");
  });

  it("opens when trigger is clicked", async () => {
    renderPanel("nmap");
    await userEvent.click(getTrigger());
    expect(screen.getByTestId("learning-panel-content")).toBeInTheDocument();
  });

  it("sets aria-expanded=true after opening", async () => {
    renderPanel("nmap");
    await userEvent.click(getTrigger());
    expect(getTrigger()).toHaveAttribute("aria-expanded", "true");
  });

  it("closes when trigger is clicked again", async () => {
    renderPanel("nmap");
    await userEvent.click(getTrigger());
    await userEvent.click(getTrigger());
    expect(screen.queryByTestId("learning-panel-content")).not.toBeInTheDocument();
  });
});

describe("ToolCheatSheet — tool content", () => {
  it("shows Nmap content for nmap", async () => {
    renderPanel("nmap");
    await userEvent.click(getTrigger());
    expect(screen.getByRole("heading", { name: /nmap quick reference/i })).toBeInTheDocument();
  });

  it("shows Nikto content for nikto", async () => {
    renderPanel("nikto");
    await userEvent.click(getTrigger());
    expect(screen.getByRole("heading", { name: /nikto quick reference/i })).toBeInTheDocument();
  });

  it("shows SQLMap content for sqlmap", async () => {
    renderPanel("sqlmap");
    await userEvent.click(getTrigger());
    expect(screen.getByRole("heading", { name: /sqlmap quick reference/i })).toBeInTheDocument();
  });

  it("switches content when activeToolId changes", async () => {
    const { rerender } = renderPanel("nmap");
    await userEvent.click(getTrigger());
    rerender(<ToolCheatSheet activeToolId="nikto" />);
    expect(screen.getByRole("heading", { name: /nikto quick reference/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /nmap quick reference/i })).not.toBeInTheDocument();
  });

  it("renders nothing for unknown tool", () => {
    const { container } = renderPanel("unknown");
    expect(container).toBeEmptyDOMElement();
  });
});
