import { describe, it, expect } from 'vitest'
import {
  isSensitiveField,
  redactValue,
  getMissingFields,
  buildCommandTokens,
  tokensToString,
  REDACTED_PLACEHOLDER,
} from '../../../src/utils/commandPreview'
import type { PluginFieldSchema } from '../../../src/api'

// ─── helpers ─────────────────────────────────────────────────────────────────

function field(overrides: Partial<PluginFieldSchema> & { id: string; label: string; type?: PluginFieldSchema['type'] }): PluginFieldSchema {
  return { type: 'string', ...overrides }
}

// ─── isSensitiveField ─────────────────────────────────────────────────────────

describe('isSensitiveField', () => {
  it('returns true for fields with sensitive:true', () => {
    expect(isSensitiveField(field({ id: 'foo', label: 'Foo', sensitive: true }))).toBe(true)
  })

  it.each([
    ['api_token', 'WPScan API Token'],
    ['password', 'Password'],
    ['auth_header', 'Authorization Header'],
    ['cookie', 'Session Cookie'],
    ['secret_key', 'Secret Key'],
    ['bearer_token', 'Bearer Token'],
    ['vault_path', 'Vault Reference'],
    ['access_key', 'Access Key'],
  ])('detects sensitive field: id=%s label=%s', (id, label) => {
    expect(isSensitiveField(field({ id, label }))).toBe(true)
  })

  it('returns false for normal fields', () => {
    expect(isSensitiveField(field({ id: 'target', label: 'Target URL' }))).toBe(false)
    expect(isSensitiveField(field({ id: 'threads', label: 'Threads' }))).toBe(false)
    expect(isSensitiveField(field({ id: 'enumerate', label: 'Enumeration Scope' }))).toBe(false)
  })
})

// ─── redactValue ─────────────────────────────────────────────────────────────

describe('redactValue', () => {
  it('redacts sensitive field values', () => {
    const f = field({ id: 'api_token', label: 'API Token' })
    expect(redactValue(f, 'super-secret')).toBe(REDACTED_PLACEHOLDER)
  })

  it('returns empty string for empty non-sensitive values', () => {
    const f = field({ id: 'target', label: 'Target' })
    expect(redactValue(f, '')).toBe('')
    expect(redactValue(f, null)).toBe('')
    expect(redactValue(f, undefined)).toBe('')
  })

  it('joins array values with commas', () => {
    const f = field({ id: 'flags', label: 'Flags', type: 'multiselect' })
    expect(redactValue(f, ['a', 'b', 'c'])).toBe('a,b,c')
  })

  it('converts non-sensitive scalar values to string', () => {
    const f = field({ id: 'threads', label: 'Threads', type: 'integer' })
    expect(redactValue(f, 10)).toBe('10')
  })
})

// ─── getMissingFields ─────────────────────────────────────────────────────────

describe('getMissingFields', () => {
  const fields: PluginFieldSchema[] = [
    field({ id: 'target', label: 'Target', required: true }),
    field({ id: 'threads', label: 'Threads', type: 'integer', required: false }),
    field({ id: 'scope', label: 'Scope', required: true }),
  ]

  it('returns required fields with empty/absent values', () => {
    const missing = getMissingFields(fields, { target: '', threads: 10, scope: '' })
    expect(missing.map((f) => f.id)).toEqual(['target', 'scope'])
  })

  it('returns empty array when all required fields are filled', () => {
    const missing = getMissingFields(fields, { target: 'example.com', threads: 5, scope: 'full' })
    expect(missing).toHaveLength(0)
  })

  it('ignores optional fields', () => {
    const missing = getMissingFields(fields, { target: 'example.com', scope: 'full' })
    expect(missing.map((f) => f.id)).not.toContain('threads')
  })
})

// ─── buildCommandTokens ───────────────────────────────────────────────────────

describe('buildCommandTokens', () => {
  const wpscanTemplate = [
    'wpscan',
    '--url',
    '{target}',
    '--enumerate',
    '{enumerate}',
    '--if:api_token:then:--api-token',
    '--if:api_token:then:{api_token}',
  ]

  const wpscanFields: PluginFieldSchema[] = [
    field({ id: 'target', label: 'Target URL', required: true }),
    field({ id: 'enumerate', label: 'Enumeration Scope' }),
    field({ id: 'api_token', label: 'WPScan API Token' }),
  ]

  it('builds tokens for a normal wpscan invocation', () => {
    const tokens = buildCommandTokens(wpscanTemplate, wpscanFields, {
      target: 'https://example.com',
      enumerate: 'vp,vt',
      api_token: '',
    })
    const plain = tokensToString(tokens)
    expect(plain).toContain('wpscan')
    expect(plain).toContain('https://example.com')
    expect(plain).toContain('vp,vt')
    expect(plain).not.toContain('--api-token')
  })

  it('redacts the api_token secret and shows flag when token is set', () => {
    const tokens = buildCommandTokens(wpscanTemplate, wpscanFields, {
      target: 'https://example.com',
      enumerate: 'vp',
      api_token: 'my-secret-token',
    })
    const plain = tokensToString(tokens)
    expect(plain).toContain(REDACTED_PLACEHOLDER)
    expect(plain).not.toContain('my-secret-token')
    expect(plain).toContain('--api-token')
  })

  it('marks missing required fields', () => {
    const tokens = buildCommandTokens(wpscanTemplate, wpscanFields, {
      target: '',
      enumerate: 'vp',
      api_token: '',
    })
    const missingToken = tokens.find((t) => t.kind === 'missing')
    expect(missingToken).toBeDefined()
    expect(missingToken?.text).toContain('Target URL')
  })

  it('first token has kind=command', () => {
    const tokens = buildCommandTokens(wpscanTemplate, wpscanFields, {
      target: 'https://example.com',
      enumerate: 'vp',
      api_token: '',
    })
    expect(tokens[0].kind).toBe('command')
    expect(tokens[0].text).toBe('wpscan')
  })

  it('uses else branch when conditional field is absent', () => {
    const template = [
      'nmap',
      '--if:safe_mode:then:-T3:else:-T4',
      '{target}',
    ]
    const fields = [
      field({ id: 'target', label: 'Target', required: true }),
      field({ id: 'safe_mode', label: 'Safe Mode', type: 'boolean' }),
    ]
    const tokensOn = buildCommandTokens(template, fields, { target: '192.168.1.1', safe_mode: true })
    expect(tokensToString(tokensOn)).toContain('-T3')

    const tokensOff = buildCommandTokens(template, fields, { target: '192.168.1.1', safe_mode: false })
    expect(tokensToString(tokensOff)).toContain('-T4')
  })
})