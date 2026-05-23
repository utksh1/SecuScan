import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getPreference, setPreference } from '../../../src/utils/preferences';

describe('preferences utility', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('returns default value when preference is not set', () => {
    const value = getPreference('test-pref', 'default');
    expect(value).toBe('default');
  });

  it('persists and retrieves a string preference', () => {
    setPreference('theme', 'dark');
    expect(getPreference('theme', 'light')).toBe('dark');
  });

  it('persists and retrieves an object preference', () => {
    const filter = { severity: 'high', type: 'technical' };
    setPreference('findings-filter', filter);
    expect(getPreference('findings-filter', {})).toEqual(filter);
  });

  it('ignores invalid JSON in localStorage and returns default', () => {
    localStorage.setItem('secuscan-pref:broken', 'undefined behavior');
    const value = getPreference('broken', 'safe-default');
    expect(value).toBe('safe-default');
  });

  it('handles localStorage unavailable gracefully', () => {
    // Mock getItem to throw (e.g. SecurityError in some browsers when cookies are blocked)
    const getItemSpy = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('Blocked!');
    });
    
    // Should return default instead of crashing
    expect(getPreference('anything', 'fallback')).toBe('fallback');
    
    getItemSpy.mockRestore();
  });

  it('handles setPreference failure gracefully', () => {
    const setItemSpy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('Quota exceeded');
    });

    // Should not crash
    expect(() => setPreference('full', 'too much data')).not.toThrow();
    
    setItemSpy.mockRestore();
  });
});
