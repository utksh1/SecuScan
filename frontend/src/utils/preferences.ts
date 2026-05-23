/**
 * Minimal localStorage-backed preference layer for SecuScan.
 * Handles persistence of UI states like filters and sort orders.
 */

const PREF_KEY_PREFIX = 'secuscan-pref:';

/**
 * Retrieves a preference from localStorage.
 * Returns defaultValue if localStorage is unavailable, key is missing, or value is invalid.
 */
export function getPreference<T>(key: string, defaultValue: T): T {
  try {
    const value = localStorage.getItem(PREF_KEY_PREFIX + key);
    if (value === null) return defaultValue;
    
    // Attempt to parse JSON. Primitive values are also valid JSON.
    return JSON.parse(value) as T;
  } catch (err) {
    // If parsing fails or localStorage is blocked, return default
    return defaultValue;
  }
}

/**
 * Stores a preference in localStorage.
 * Fails silently if localStorage is unavailable.
 */
export function setPreference<T>(key: string, value: T): void {
  try {
    localStorage.setItem(PREF_KEY_PREFIX + key, JSON.stringify(value));
  } catch (err) {
    // Silently ignore storage failures (e.g. private mode, quota exceeded)
  }
}
