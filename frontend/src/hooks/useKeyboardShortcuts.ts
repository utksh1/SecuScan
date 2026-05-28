import { useShortcuts } from "../context/ShortcutContext";

/**
 * Convenience hook — exposes the full shortcut registry and controls.
 * Components can call this to read bindings or open the cheatsheet programmatically.
 */
export const useKeyboardShortcuts = () => {
  return useShortcuts();
};
