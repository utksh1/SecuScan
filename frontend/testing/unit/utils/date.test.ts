import { describe, test, expect, beforeEach } from "vitest";

import {
  parseDateSafe,
  formatDateLong,
  formatLocaleDate,
  formatLocaleTime,
  getCurrentTimeZone,
  formatTaskInit,
} from "../../../src/utils/date";
  
  describe("date utilities", () => {
    beforeEach(() => {
      localStorage.clear();
    });
  
    describe("parseDateSafe", () => {
      test("parses ISO timestamp", () => {
        const result = parseDateSafe("2026-05-12T10:30:00Z");
        expect(result).not.toBeNull();
        expect(result instanceof Date).toBe(true);
      });
  
      test("parses SQLite timestamp", () => {
        const result = parseDateSafe("2026-05-12 10:30:00");
        expect(result).not.toBeNull();
      });
  
      test("returns null for invalid input", () => {
        expect(parseDateSafe("invalid-date")).toBeNull();
      });
  
      test("returns null for empty string", () => {
        expect(parseDateSafe("")).toBeNull();
      });
  
      test("returns null for null input", () => {
        expect(parseDateSafe(null)).toBeNull();
      });
    });
  
    describe("formatDateLong", () => {
      test("formats valid date", () => {
        const result = formatDateLong("2026-05-12T10:30:00Z");
        expect(result).not.toBe("N/A");
        expect(result).toContain("2026");
      });
  
      test("returns N/A for invalid input", () => {
        expect(formatDateLong("bad-date")).toBe("N/A");
      });
    });
  
    describe("formatLocaleDate", () => {
      test("formats valid date", () => {
        const result = formatLocaleDate("2026-05-12T10:30:00Z");
        expect(result).not.toBe("N/A");
      });
  
      test("returns N/A for invalid input", () => {
        expect(formatLocaleDate("bad-date")).toBe("N/A");
      });
    });
  
    describe("formatLocaleTime", () => {
      test("formats valid time", () => {
        const result = formatLocaleTime("2026-05-12T10:30:00Z");
        expect(result).not.toBe("N/A");
      });
  
      test("returns N/A for invalid input", () => {
        expect(formatLocaleTime("bad-date")).toBe("N/A");
      });
    });
  
    describe("timezone preference safety", () => {
      test("does not crash without localStorage config", () => {
        expect(() => formatLocaleDate("2026-05-12T10:30:00Z")).not.toThrow();
      });
  
      test("uses fallback timezone safely", () => {
        expect(getCurrentTimeZone()).toBeTruthy();
      });
    });
  
    describe("formatTaskInit", () => {
      test("returns UNKNOWN values for invalid date", () => {
        const result = formatTaskInit("bad-date");
        expect(result.date).toBe("UNKNOWN DATE");
        expect(result.time).toBe("UNKNOWN TIME");
      });
  
      test("formats valid task date", () => {
        const result = formatTaskInit("2026-05-12T10:30:00Z");
        expect(result.date).not.toBe("UNKNOWN DATE");
        expect(result.time).not.toBe("UNKNOWN TIME");
      });
    });
  });