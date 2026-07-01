/**
 * Schema coverage for src/data/scanTools.ts (issue #1416).
 *
 * These tests verify that every entry in the scanTools array conforms to the
 * ScanTool interface contract: required fields are present, enum fields
 * have valid literal values, and id uniqueness is enforced.
 */

import { describe, it, expect } from 'vitest'
import { scanTools, type ScanTool } from '../../../src/data/scanTools'

const RISK_LEVELS = ['passive', 'active', 'aggressive'] as const
const PRESET_COMPATIBILITY = ['quick-recon', 'deep-scan', 'both', 'none'] as const

const REQUIRED_FIELDS: Array<keyof ScanTool> = [
    'id',
    'name',
    'purpose',
    'riskLevel',
    'presetCompatibility',
    'requiresConsent',
    'category',
]

describe('scanTools catalog — schema contract', () => {
    it('exports a non-empty array', () => {
        expect(Array.isArray(scanTools)).toBe(true)
        expect(scanTools.length).toBeGreaterThan(0)
    })

    it('every tool id is a non-empty string and unique', () => {
        const ids = scanTools.map(t => t.id)
        const unique = new Set(ids)
        expect(unique.size).toBe(ids.length)
        for (const id of ids) {
            expect(typeof id).toBe('string')
            expect(id.length).toBeGreaterThan(0)
        }
    })

    it('every tool has all required fields', () => {
        for (const tool of scanTools) {
            for (const field of REQUIRED_FIELDS) {
                expect(tool).toHaveProperty(field)
            }
        }
    })

    it('riskLevel is one of the defined literals', () => {
        for (const tool of scanTools) {
            expect(RISK_LEVELS).toContain(tool.riskLevel)
        }
    })

    it('presetCompatibility is one of the defined literals', () => {
        for (const tool of scanTools) {
            expect(PRESET_COMPATIBILITY).toContain(tool.presetCompatibility)
        }
    })

    it('requiresConsent is a boolean', () => {
        for (const tool of scanTools) {
            expect(typeof tool.requiresConsent).toBe('boolean')
        }
    })

    it('name and purpose are non-empty strings', () => {
        for (const tool of scanTools) {
            expect(typeof tool.name).toBe('string')
            expect(tool.name.length).toBeGreaterThan(0)
            expect(typeof tool.purpose).toBe('string')
            expect(tool.purpose.length).toBeGreaterThan(0)
        }
    })

    it('category is a non-empty string', () => {
        for (const tool of scanTools) {
            expect(typeof tool.category).toBe('string')
            expect(tool.category.length).toBeGreaterThan(0)
        }
    })

    it('subcategory, if present, is a non-empty string', () => {
        for (const tool of scanTools) {
            if (tool.subcategory !== undefined) {
                expect(typeof tool.subcategory).toBe('string')
                expect(tool.subcategory.length).toBeGreaterThan(0)
            }
        }
    })

    it('disabled and isQuickStart, if present, are booleans', () => {
        for (const tool of scanTools) {
            if (tool.disabled !== undefined) {
                expect(typeof tool.disabled).toBe('boolean')
            }
            if (tool.isQuickStart !== undefined) {
                expect(typeof tool.isQuickStart).toBe('boolean')
            }
        }
    })

    it('disabledReason, if present, is a non-empty string', () => {
        for (const tool of scanTools) {
            if (tool.disabledReason !== undefined) {
                expect(typeof tool.disabledReason).toBe('string')
                expect(tool.disabledReason.length).toBeGreaterThan(0)
            }
        }
    })

    it('nmap entry is present and has expected values', () => {
        const nmap = scanTools.find(t => t.id === 'nmap')
        expect(nmap).toBeDefined()
        expect(nmap!.riskLevel).toBe('active')
        expect(nmap!.presetCompatibility).toBe('both')
        expect(nmap!.requiresConsent).toBe(true)
        expect(nmap!.category).toBe('recon')
    })
})
