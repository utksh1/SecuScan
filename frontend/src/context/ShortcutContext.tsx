import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../routes";

export interface ShortcutBinding {
  id: string;
  keys: string;
  description: string;
  category: "Navigation" | "Actions" | "UI";
}

const DEFAULT_SHORTCUTS: ShortcutBinding[] = [
  { id: "go_dashboard",  keys: "g d", description: "Go to Dashboard",      category: "Navigation" },
  { id: "go_scans",      keys: "g s", description: "Go to Scans",          category: "Navigation" },
  { id: "go_findings",   keys: "g f", description: "Go to Findings",       category: "Navigation" },
  { id: "go_toolkit",    keys: "g t", description: "Go to Toolkit",        category: "Navigation" },
  { id: "new_scan",      keys: "n",   description: "New scan dialog",      category: "Actions"    },
  { id: "open_filters",  keys: "/",   description: "Focus filter input",   category: "UI"         },
  { id: "open_cheatsheet", keys: "?", description: "Toggle cheatsheet",    category: "UI"         },
];

const STORAGE_KEY = "secuscan:shortcuts";

interface ShortcutContextValue {
  shortcuts: ShortcutBinding[];
  updateBinding: (id: string, newKeys: string) => void;
  resetToDefaults: () => void;
  cheatsheetOpen: boolean;
  setCheatsheetOpen: (open: boolean) => void;
}

const ShortcutContext = createContext<ShortcutContextValue | null>(null);

export const ShortcutProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();

  const loadShortcuts = (): ShortcutBinding[] => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return DEFAULT_SHORTCUTS;
      const overrides: Record<string, string> = JSON.parse(stored);
      return DEFAULT_SHORTCUTS.map((s) =>
        overrides[s.id] ? { ...s, keys: overrides[s.id] } : s
      );
    } catch {
      return DEFAULT_SHORTCUTS;
    }
  };

  const [shortcuts, setShortcuts] = useState<ShortcutBinding[]>(loadShortcuts);
  const [cheatsheetOpen, setCheatsheetOpen] = useState(false);
  const pendingKeysRef = useRef<string[]>([]);
  const pendingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const updateBinding = useCallback((id: string, newKeys: string) => {
    setShortcuts((prev) => {
      const updated = prev.map((s) => (s.id === id ? { ...s, keys: newKeys } : s));
      const overrides: Record<string, string> = {};
      updated.forEach((s) => {
        const def = DEFAULT_SHORTCUTS.find((d) => d.id === s.id);
        if (def && def.keys !== s.keys) overrides[s.id] = s.keys;
      });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
      return updated;
    });
  }, []);

  const resetToDefaults = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setShortcuts(DEFAULT_SHORTCUTS);
  }, []);

  const ROUTE_MAP: Record<string, string> = {
    go_dashboard: routes.dashboard,
    go_scans:     routes.scans,
    go_findings:  routes.findings,
    go_toolkit:   routes.toolkit,
  };

  const executeShortcut = useCallback(
    (id: string) => {
      if (ROUTE_MAP[id]) { navigate(ROUTE_MAP[id]); return; }
      if (id === "open_cheatsheet") { setCheatsheetOpen((o) => !o); return; }
      if (id === "open_filters") {
        const el = document.querySelector<HTMLInputElement>("[data-shortcut-target='filter'], input[type='search']");
        el?.focus();
        return;
      }
    },
    [navigate]
  );

  useEffect(() => {
    const isTyping = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      return ["INPUT", "TEXTAREA", "SELECT"].includes(tag);
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (isTyping(e) && e.key !== "Escape") return;

      // Normalize key: for printable single chars, ignore Shift modifier
      const isPrintableChar = e.key.length === 1 && !e.ctrlKey && !e.altKey;
      const mod = [
        e.ctrlKey  ? "Ctrl"  : "",
        !isPrintableChar && e.shiftKey ? "Shift" : "",
        e.altKey   ? "Alt"   : "",
      ].filter(Boolean).join("+");

      const key = mod ? `${mod}+${e.key}` : e.key;

      // Single-key match first
      const single = shortcuts.find((s) => s.keys === key);
      if (single) { e.preventDefault(); executeShortcut(single.id); return; }

      // Sequential key combo (e.g. "g d")
      if (pendingTimerRef.current) clearTimeout(pendingTimerRef.current);
      const next = [...pendingKeysRef.current, key];
      const combo = next.join(" ");

      const match = shortcuts.find((s) => s.keys === combo);
      if (match) {
        e.preventDefault();
        pendingKeysRef.current = [];
        executeShortcut(match.id);
        return;
      }

      // Check if any shortcut starts with the current sequence
      const partial = shortcuts.some((s) => s.keys.startsWith(combo + " "));
      if (partial) {
        pendingKeysRef.current = next;
        const t = setTimeout(() => { pendingKeysRef.current = []; }, 1500);
        pendingTimerRef.current = t;
      } else {
        pendingKeysRef.current = [];
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [shortcuts, executeShortcut]);

  return (
    <ShortcutContext.Provider value={{ shortcuts, updateBinding, resetToDefaults, cheatsheetOpen, setCheatsheetOpen }}>
      {children}
    </ShortcutContext.Provider>
  );
};

export const useShortcuts = () => {
  const ctx = useContext(ShortcutContext);
  if (!ctx) throw new Error("useShortcuts must be used inside ShortcutProvider");
  return ctx;
};
