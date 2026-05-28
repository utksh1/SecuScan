import React, { useEffect, useRef, useState } from "react";
import { useShortcuts } from "../context/ShortcutContext";

const CATEGORIES = ["Navigation", "Actions", "UI"] as const;

const Kbd: React.FC<{ keys: string }> = ({ keys }) => (
  <span style={{ display: "inline-flex", gap: "4px", flexWrap: "wrap" }}>
    {keys.split(" ").map((k, i) => (
      <kbd
        key={i}
        style={{
          padding: "2px 8px",
          borderRadius: "5px",
          border: "1px solid #444",
          background: "#1e1e1e",
          color: "#e0e0e0",
          fontFamily: "monospace",
          fontSize: "12px",
          boxShadow: "0 2px 0 #333",
        }}
      >
        {k}
      </kbd>
    ))}
  </span>
);

export const ShortcutCheatsheet: React.FC = () => {
  const { shortcuts, updateBinding, resetToDefaults, cheatsheetOpen, setCheatsheetOpen } = useShortcuts();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [capturedKeys, setCapturedKeys] = useState<string>("");
  const overlayRef = useRef<HTMLDivElement>(null);
  const pendingKeysRef = useRef<string[]>([]);

  // Close on Escape (only when not editing)
  useEffect(() => {
    if (!cheatsheetOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !editingId) {
        e.preventDefault();
        e.stopPropagation();
        setCheatsheetOpen(false);
      }
    };
    document.addEventListener("keydown", handleKey, true);
    return () => document.removeEventListener("keydown", handleKey, true);
  }, [cheatsheetOpen, editingId, setCheatsheetOpen]);

  // Trap focus inside overlay
  useEffect(() => {
    if (cheatsheetOpen) overlayRef.current?.focus();
  }, [cheatsheetOpen]);

  const handleCapture = (e: React.KeyboardEvent) => {
    e.preventDefault();
    if (e.key === "Escape") { setEditingId(null); setCapturedKeys(""); pendingKeysRef.current = []; return; }
    if (e.key === "Enter" && capturedKeys && editingId) {
      const final = pendingKeysRef.current.length > 0
        ? [...pendingKeysRef.current, capturedKeys].join(" ")
        : capturedKeys;
      updateBinding(editingId, final);
      setEditingId(null);
      setCapturedKeys("");
      pendingKeysRef.current = [];
      return;
    }

    // Filter out modifier-only keys
    const isModifierOnly = ["Shift", "Control", "Alt", "Meta"].includes(e.key);
    if (isModifierOnly) return;

    // Normalize key: for printable single chars, ignore Shift modifier
    const isPrintableChar = e.key.length === 1 && !e.ctrlKey && !e.altKey;
    const mod = [
      e.ctrlKey  ? "Ctrl"  : "",
      !isPrintableChar && e.shiftKey ? "Shift" : "",
      e.altKey   ? "Alt"   : "",
    ].filter(Boolean).join("+");
    const key = mod ? `${mod}+${e.key}` : e.key;

    // For sequences, accumulate in ref; for single keys, just display
    if (pendingKeysRef.current.length > 0) {
      // Building a sequence like "g d"
      pendingKeysRef.current.push(key);
      setCapturedKeys(pendingKeysRef.current.join(" "));
    } else {
      // First key pressed
      setCapturedKeys(key);
      pendingKeysRef.current = [key];
    }
  };

  if (!cheatsheetOpen) return null;

  return (
    <div
      style={{
        position: "fixed", inset: 0, zIndex: 9999,
        background: "rgba(0,0,0,0.75)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
      onClick={(e) => { if (e.target === e.currentTarget) setCheatsheetOpen(false); }}
    >
      <div
        ref={overlayRef}
        tabIndex={-1}
        style={{
          background: "#111",
          border: "1px solid #333",
          borderRadius: "12px",
          width: "560px",
          maxWidth: "95vw",
          maxHeight: "85vh",
          overflowY: "auto",
          outline: "none",
          boxShadow: "0 25px 60px rgba(0,0,0,0.6)",
        }}
      >
        {/* Header */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          padding: "20px 24px 16px",
          borderBottom: "1px solid #222",
        }}>
          <div>
            <h2 style={{ margin: 0, color: "#fff", fontSize: "16px", fontWeight: 600 }}>
              Keyboard Shortcuts
            </h2>
            <p style={{ margin: "4px 0 0", color: "#666", fontSize: "12px" }}>
              Press <Kbd keys="?" /> anywhere to toggle • Click Edit to remap
            </p>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              onClick={resetToDefaults}
              style={{
                background: "transparent", border: "1px solid #333",
                color: "#888", borderRadius: "6px",
                padding: "5px 12px", cursor: "pointer", fontSize: "12px",
              }}
            >
              Reset all
            </button>
            <button
              onClick={() => setCheatsheetOpen(false)}
              style={{
                background: "transparent", border: "none",
                color: "#666", cursor: "pointer", fontSize: "20px", lineHeight: 1,
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: "8px 24px 24px" }}>
          {CATEGORIES.map((cat) => (
            <div key={cat} style={{ marginTop: "20px" }}>
              <p style={{
                margin: "0 0 10px", fontSize: "11px",
                fontWeight: 600, textTransform: "uppercase",
                letterSpacing: "0.08em", color: "#555",
              }}>
                {cat}
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                {shortcuts.filter((s) => s.category === cat).map((s) => (
                  <div
                    key={s.id}
                    style={{
                      display: "flex", alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px", borderRadius: "7px",
                      background: editingId === s.id ? "#1a1a2e" : "#161616",
                      border: editingId === s.id ? "1px solid #4a4aff" : "1px solid transparent",
                    }}
                  >
                    <span style={{ color: "#ccc", fontSize: "13px" }}>{s.description}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      {editingId === s.id ? (
                        <input
                          autoFocus
                          onKeyDown={handleCapture}
                          value={capturedKeys || "Press keys…"}
                          readOnly
                          style={{
                            background: "#0d0d1a", border: "1px solid #4a4aff",
                            color: "#7a7aff", borderRadius: "5px",
                            padding: "3px 10px", fontSize: "12px",
                            fontFamily: "monospace", width: "120px",
                            cursor: "default", outline: "none",
                          }}
                        />
                      ) : (
                        <Kbd keys={s.keys} />
                      )}
                      <button
                        onClick={() => {
                          if (editingId === s.id) { setEditingId(null); setCapturedKeys(""); }
                          else { setEditingId(s.id); setCapturedKeys(""); }
                        }}
                        style={{
                          background: "transparent",
                          border: "1px solid #2a2a2a",
                          color: editingId === s.id ? "#7a7aff" : "#555",
                          borderRadius: "5px", padding: "3px 9px",
                          cursor: "pointer", fontSize: "11px",
                        }}
                      >
                        {editingId === s.id ? "Cancel" : "Edit"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
