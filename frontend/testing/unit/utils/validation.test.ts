import { describe, it, expect } from 'vitest'
import { getValidationError, isFormValid } from '../../../src/utils/validation'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function field(overrides: Partial<{
  id: string
  label: string
  type: string
  required: boolean
  validation: Record<string, unknown>
}> = {}) {
  return {
    id: 'target',
    label: 'Target',
    type: 'string',
    required: false,
    validation: {},
    ...overrides,
  }
}

// ─── Required field ───────────────────────────────────────────────────────────

describe('getValidationError – required fields', () => {
  it('returns error for empty required string', () => {
    expect(getValidationError(field({ required: true }), '')).toBeTruthy()
  })

  it('returns error for whitespace-only required string', () => {
    expect(getValidationError(field({ required: true }), '   ')).toBeTruthy()
  })

  it('returns error for null required field', () => {
    expect(getValidationError(field({ required: true }), null)).toBeTruthy()
  })

  it('returns error for empty array required multiselect', () => {
    expect(getValidationError(field({ required: true }), [])).toBeTruthy()
  })

  it('returns null for valid required string', () => {
    expect(getValidationError(field({ required: true }), 'example.com')).toBeNull()
  })

  it('returns null for non-required empty field', () => {
    expect(getValidationError(field({ required: false }), '')).toBeNull()
  })
})

// ─── validation_type presets ──────────────────────────────────────────────────

describe('getValidationError – validation_type: url', () => {
  const f = field({ validation: { validation_type: 'url' } })

  it('accepts valid http URL', () => {
    expect(getValidationError(f, 'http://example.com')).toBeNull()
  })

  it('accepts valid https URL', () => {
    expect(getValidationError(f, 'https://sub.example.com/path?q=1')).toBeNull()
  })

  it('rejects bare domain', () => {
    expect(getValidationError(f, 'example.com')).toBeTruthy()
  })

  it('rejects ftp URL', () => {
    expect(getValidationError(f, 'ftp://example.com')).toBeTruthy()
  })
})

describe('getValidationError – validation_type: hostname', () => {
  const f = field({ validation: { validation_type: 'hostname' } })

  it('accepts simple hostname', () => {
    expect(getValidationError(f, 'example.com')).toBeNull()
  })

  it('accepts subdomain', () => {
    expect(getValidationError(f, 'sub.example.com')).toBeNull()
  })

  it('rejects hostname with scheme', () => {
    expect(getValidationError(f, 'https://example.com')).toBeTruthy()
  })

  it('rejects hostname with spaces', () => {
    expect(getValidationError(f, 'exam ple.com')).toBeTruthy()
  })
})

describe('getValidationError – validation_type: domain', () => {
  const f = field({ validation: { validation_type: 'domain' } })

  it('accepts valid domain', () => {
    expect(getValidationError(f, 'example.com')).toBeNull()
  })

  it('rejects domain with http scheme', () => {
    expect(getValidationError(f, 'http://example.com')).toBeTruthy()
  })

  it('rejects bare word without dot', () => {
    expect(getValidationError(f, 'localhost')).toBeTruthy()
  })
})

describe('getValidationError – validation_type: ipv4', () => {
  const f = field({ validation: { validation_type: 'ipv4' } })

  it('accepts valid IPv4', () => {
    expect(getValidationError(f, '192.168.1.1')).toBeNull()
  })

  it('accepts 0.0.0.0', () => {
    expect(getValidationError(f, '0.0.0.0')).toBeNull()
  })

  it('rejects octet > 255', () => {
    expect(getValidationError(f, '256.0.0.1')).toBeTruthy()
  })

  it('rejects partial IP', () => {
    expect(getValidationError(f, '192.168.1')).toBeTruthy()
  })
})

describe('getValidationError – validation_type: port', () => {
  const f = field({ validation: { validation_type: 'port' } })

  it('accepts port 80', () => {
    expect(getValidationError(f, '80')).toBeNull()
  })

  it('accepts port 65535', () => {
    expect(getValidationError(f, '65535')).toBeNull()
  })

  it('rejects port 0', () => {
    expect(getValidationError(f, '0')).toBeTruthy()
  })

  it('rejects port 65536', () => {
    expect(getValidationError(f, '65536')).toBeTruthy()
  })
})

describe('getValidationError – validation_type: cidr', () => {
  const f = field({ validation: { validation_type: 'cidr' } })

  it('accepts valid CIDR', () => {
    expect(getValidationError(f, '192.168.1.0/24')).toBeNull()
  })

  it('accepts /32', () => {
    expect(getValidationError(f, '10.0.0.1/32')).toBeNull()
  })

  it('rejects CIDR with prefix > 32', () => {
    expect(getValidationError(f, '10.0.0.0/33')).toBeTruthy()
  })

  it('rejects plain IP without prefix', () => {
    expect(getValidationError(f, '10.0.0.1')).toBeTruthy()
  })
})

// ─── Raw pattern validation ───────────────────────────────────────────────────

describe('getValidationError – raw pattern (backwards compat)', () => {
  const f = field({ validation: { pattern: '^[a-z]+$' } })

  it('accepts value matching pattern', () => {
    expect(getValidationError(f, 'abc')).toBeNull()
  })

  it('rejects value not matching pattern', () => {
    expect(getValidationError(f, 'ABC123')).toBeTruthy()
  })

  it('uses custom message when provided', () => {
    const fWithMsg = field({ validation: { pattern: '^[a-z]+$', message: 'lowercase only' } })
    expect(getValidationError(fWithMsg, 'ABC')).toBe('lowercase only')
  })

  it('does not crash on malformed regex', () => {
    const fBad = field({ validation: { pattern: '[invalid(' } })
    expect(() => getValidationError(fBad, 'abc')).not.toThrow()
  })
})

// ─── Integer min/max ──────────────────────────────────────────────────────────

describe('getValidationError – integer min/max', () => {
  const f = field({ type: 'integer', validation: { min: 1, max: 100 } })

  it('accepts value within range', () => {
    expect(getValidationError(f, 50)).toBeNull()
  })

  it('accepts boundary min', () => {
    expect(getValidationError(f, 1)).toBeNull()
  })

  it('accepts boundary max', () => {
    expect(getValidationError(f, 100)).toBeNull()
  })

  it('rejects value below min', () => {
    expect(getValidationError(f, 0)).toBeTruthy()
  })

  it('rejects value above max', () => {
    expect(getValidationError(f, 101)).toBeTruthy()
  })

  it('rejects non-integer float', () => {
    expect(getValidationError(f, 1.5)).toBeTruthy()
  })

  it('skips check for empty string (not yet entered)', () => {
    expect(getValidationError(f, '')).toBeNull()
  })
})

// ─── isFormValid ──────────────────────────────────────────────────────────────

describe('isFormValid', () => {
  const fields = [
    field({ id: 'target', label: 'Target', required: true, validation: { validation_type: 'url' } }),
    field({ id: 'threads', label: 'Threads', type: 'integer', required: false, validation: { min: 1, max: 50 } }),
  ]

  it('returns true when all fields are valid', () => {
    expect(isFormValid(fields, { target: 'https://example.com', threads: 5 })).toBe(true)
  })

  it('returns false when required field is empty', () => {
    expect(isFormValid(fields, { target: '', threads: 5 })).toBe(false)
  })

  it('returns false when a field fails pattern validation', () => {
    expect(isFormValid(fields, { target: 'not-a-url', threads: 5 })).toBe(false)
  })

  it('returns false when integer is out of range', () => {
    expect(isFormValid(fields, { target: 'https://example.com', threads: 999 })).toBe(false)
  })
})