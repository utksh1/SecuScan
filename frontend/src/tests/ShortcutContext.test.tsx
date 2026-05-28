import { render, screen, fireEvent, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ShortcutProvider, useShortcuts } from "../context/ShortcutContext";
import { ShortcutCheatsheet } from "../components/ShortcutCheatsheet";

// Helper wrapper
const Wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ShortcutProvider>{children}</ShortcutProvider>
  </MemoryRouter>
);

// Test component to expose context values
const TestConsumer: React.FC = () => {
  const { shortcuts, updateBinding, resetToDefaults } = useShortcuts();
  return (
    <div>
      {shortcuts.map((s) => (
        <div key={s.id} data-testid={`shortcut-${s.id}`}>{s.keys}</div>
      ))}
      <button onClick={() => updateBinding("go_scans", "Ctrl+1")}>Update</button>
      <button onClick={resetToDefaults}>Reset</button>
    </div>
  );
};

// ─── Tests ───────────────────────────────────────────────────────────────────

describe("ShortcutContext", () => {
  beforeEach(() => localStorage.clear());

  test("loads default bindings on first render", () => {
    render(<TestConsumer />, { wrapper: Wrapper });
    expect(screen.getByTestId("shortcut-go_scans").textContent).toBe("g s");
    expect(screen.getByTestId("shortcut-go_dashboard").textContent).toBe("g d");
  });

  test("updateBinding changes the key for a shortcut", () => {
    render(<TestConsumer />, { wrapper: Wrapper });
    fireEvent.click(screen.getByText("Update"));
    expect(screen.getByTestId("shortcut-go_scans").textContent).toBe("Ctrl+1");
  });

  test("updateBinding persists override to localStorage", () => {
    render(<TestConsumer />, { wrapper: Wrapper });
    fireEvent.click(screen.getByText("Update"));
    const stored = JSON.parse(localStorage.getItem("secuscan:shortcuts") ?? "{}");
    expect(stored["go_scans"]).toBe("Ctrl+1");
  });

  test("resetToDefaults restores original bindings", () => {
    render(<TestConsumer />, { wrapper: Wrapper });
    fireEvent.click(screen.getByText("Update"));
    fireEvent.click(screen.getByText("Reset"));
    expect(screen.getByTestId("shortcut-go_scans").textContent).toBe("g s");
  });

  test("resetToDefaults clears localStorage", () => {
    render(<TestConsumer />, { wrapper: Wrapper });
    fireEvent.click(screen.getByText("Update"));
    fireEvent.click(screen.getByText("Reset"));
    expect(localStorage.getItem("secuscan:shortcuts")).toBeNull();
  });

  test("shortcuts reload persisted overrides on mount", () => {
    localStorage.setItem("secuscan:shortcuts", JSON.stringify({ go_scans: "Ctrl+2" }));
    render(<TestConsumer />, { wrapper: Wrapper });
    expect(screen.getByTestId("shortcut-go_scans").textContent).toBe("Ctrl+2");
  });
});

describe("Keyboard event guard", () => {
  test("shortcut does NOT fire when typing in an input", () => {
    const { container } = render(
      <Wrapper>
        <input data-testid="search" type="search" />
        <ShortcutCheatsheet />
      </Wrapper>
    );
    const input = screen.getByTestId("search");
    input.focus();
    fireEvent.keyDown(input, { key: "?" });
    // cheatsheet should NOT open
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("shortcut does NOT fire inside contenteditable", () => {
    render(
      <Wrapper>
        <div data-testid="editor" contentEditable suppressContentEditableWarning />
        <ShortcutCheatsheet />
      </Wrapper>
    );
    const editor = screen.getByTestId("editor");
    editor.focus();
    fireEvent.keyDown(editor, { key: "?" });
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("? key opens cheatsheet when focused on body", () => {
    render(
      <Wrapper>
        <ShortcutCheatsheet />
      </Wrapper>
    );
    act(() => {
      fireEvent.keyDown(document, { key: "?" });
    });
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

describe("ShortcutCheatsheet overlay", () => {
  test("renders all 3 categories", () => {
    render(
      <Wrapper>
        <ShortcutCheatsheet />
      </Wrapper>
    );
    act(() => { fireEvent.keyDown(document, { key: "?" }); });
    expect(screen.getByText("Navigation")).toBeInTheDocument();
    expect(screen.getByText("Actions")).toBeInTheDocument();
    expect(screen.getByText("UI")).toBeInTheDocument();
  });

  test("Reset all button calls resetToDefaults", () => {
    render(
      <Wrapper>
        <TestConsumer />
        <ShortcutCheatsheet />
      </Wrapper>
    );
    act(() => { fireEvent.keyDown(document, { key: "?" }); });
    fireEvent.click(screen.getByText("Update")); // set override
    fireEvent.click(screen.getByText("Reset all")); // reset via cheatsheet
    expect(screen.getByTestId("shortcut-go_scans").textContent).toBe("g s");
  });

  test("has correct ARIA role and aria-modal", () => {
    render(<Wrapper><ShortcutCheatsheet /></Wrapper>);
    act(() => { fireEvent.keyDown(document, { key: "?" }); });
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
  });
});
