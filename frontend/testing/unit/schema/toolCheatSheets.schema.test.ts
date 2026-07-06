/**
 * Schema coverage for src/data/toolCheatSheets.ts (issue #1417).
 *
 * These tests verify that the cheat-sheet data conforms to its TypeScript
 * interface contract: every tool entry has the required fields, each flag
 * has a non-empty flag and description, and the ethical tip is present.
 */

import { describe, it, expect } from 'vitest'
import toolCheatSheets, { type CheatSheet } from '../../../src/data/toolCheatSheets'

const SCHEMA_FIELDS: Array<keyof CheatSheet> = [
    'toolId',
    'toolName',
    'overview',
    'flags',
    'ethicalTip',
]

describe('toolCheatSheets — schema contract', () => {
    it('exports at least one entry', () => {
        expect(Object.keys(toolCheatSheets).length).toBeGreaterThan(0)
    })

    it('every entry has all required top-level fields', () => {
        for (const [toolId, sheet] of Object.entries(toolCheatSheets)) {
            for (const field of SCHEMA_FIELDS) {
                expect(sheet).toHaveProperty(field)
            }
            // toolId in data should match the Record key
            expect(sheet.toolId).toBe(toolId)
        }
    })

    it('every toolId is a non-empty string', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            expect(typeof sheet.toolId).toBe('string')
            expect(sheet.toolId.length).toBeGreaterThan(0)
        }
    })

    it('every toolName is a non-empty string', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            expect(typeof sheet.toolName).toBe('string')
            expect(sheet.toolName.length).toBeGreaterThan(0)
        }
    })

    it('every overview is a non-empty string', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            expect(typeof sheet.overview).toBe('string')
            expect(sheet.overview.length).toBeGreaterThan(0)
        }
    })

    it('flags is always a non-empty array', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            expect(Array.isArray(sheet.flags)).toBe(true)
            expect(sheet.flags.length).toBeGreaterThan(0)
        }
    })

    it('every flag has a non-empty flag string and description', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            for (const f of sheet.flags) {
                expect(typeof f.flag).toBe('string')
                expect(f.flag.length).toBeGreaterThan(0)
                expect(typeof f.description).toBe('string')
                expect(f.description.length).toBeGreaterThan(0)
            }
        }
    })

    it('no flag objects are empty', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            for (const f of sheet.flags) {
                expect(Object.keys(f).sort()).toEqual(['description', 'flag'])
            }
        }
    })

    it('every ethicalTip is a non-empty string', () => {
        for (const sheet of Object.values(toolCheatSheets)) {
            expect(typeof sheet.ethicalTip).toBe('string')
            expect(sheet.ethicalTip.length).toBeGreaterThan(0)
        }
    })

    it('nmap entry is present and has expected shape', () => {
        const nmap = toolCheatSheets['nmap']
        expect(nmap).toBeDefined()
        expect(nmap.toolName).toBe('Nmap')
        expect(nmap.flags.some(f => f.flag === '-sn')).toBe(true)
        expect(nmap.flags.some(f => f.flag === '-sV')).toBe(true)
    })
})
