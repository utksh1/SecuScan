import type { PluginFieldSchema } from '../api'

// ─── Sensitive field detection ────────────────────────────────────────────────

const SENSITIVE_PATTERNS: RegExp[] = [
  /\bpassword\b/,
  /\bpasswd\b/,
  /\bsecret\b/,
  /\btoken\b/,
  /\bapi[_\s-]?key\b/,
  /\bapikey\b/,
  /\bauth\b/,
  /\bauthorization\b/,
  /\bcookie\b/,
  /\bcredential\b/,
  /\bprivate[_\s-]?key\b/,
  /\bvault\b/,
  /\bbearer\b/,
  /\baccess[_\s-]?key\b/,
  /\bsecret[_\s-]?key\b/,
]

export function isSensitiveField(field: PluginFieldSchema): boolean {
  if (field.sensitive) return true
  const haystack = `${field.id} ${field.label}`.toLowerCase()
  return SENSITIVE_PATTERNS.some((re) => re.test(haystack))
}

// ─── Redaction ────────────────────────────────────────────────────────────────

export const REDACTED_PLACEHOLDER = '[REDACTED]'

export function redactValue(field: PluginFieldSchema, value: unknown): string {
  if (isSensitiveField(field)) return REDACTED_PLACEHOLDER
  if (value === null || value === undefined || value === '') return ''
  if (Array.isArray(value)) return value.join(',')
  return String(value)
}

// ─── Missing required fields ──────────────────────────────────────────────────

export interface MissingField {
  id: string
  label: string
}

export function getMissingFields(
  fields: PluginFieldSchema[],
  inputs: Record<string, unknown>,
): MissingField[] {
  return fields
    .filter((field) => {
      if (!field.required) return false
      const val = inputs[field.id]
      if (val === undefined || val === null) return true
      if (typeof val === 'string') return val.trim().length === 0
      if (Array.isArray(val)) return val.length === 0
      return false
    })
    .map((f) => ({ id: f.id, label: f.label }))
}

// ─── Command token builder ────────────────────────────────────────────────────

export interface PreviewToken {
  text: string
  kind: 'command' | 'flag' | 'value' | 'redacted' | 'missing' | 'placeholder'
}

/**
 * Build a sanitized, tokenized preview of the command that will be executed.
 * Handles the `--if:field:then:A:else:B` conditional syntax used in plugin
 * command_template arrays, redacting sensitive values and marking missing ones.
 */
export function buildCommandTokens(
  commandTemplate: string[],
  fields: PluginFieldSchema[],
  inputs: Record<string, unknown>,
): PreviewToken[] {
  const fieldMap = Object.fromEntries(fields.map((f) => [f.id, f]))
  const tokens: PreviewToken[] = []

  for (const segment of commandTemplate) {
    // ── Conditional: --if:field:then:A[:else:B] ──────────────────────────────
    const ifMatch = segment.match(/^--if:([^:]+):then:([^:]*)(?::else:(.*))?$/)
    if (ifMatch) {
      const [, fieldId, thenVal, elseVal] = ifMatch
      const field = fieldMap[fieldId]
      const rawValue = inputs[fieldId]
      const hasValue =
        rawValue !== undefined &&
        rawValue !== null &&
        rawValue !== '' &&
        rawValue !== false &&
        !(Array.isArray(rawValue) && rawValue.length === 0)

      const chosen = hasValue ? thenVal : (elseVal ?? '')
      if (!chosen) continue

      // The chosen branch might itself be a flag (starts with -) or a literal
      if (chosen.startsWith('-')) {
        tokens.push({ text: chosen, kind: 'flag' })
      } else if (field && isSensitiveField(field) && hasValue) {
        tokens.push({ text: REDACTED_PLACEHOLDER, kind: 'redacted' })
      } else {
        tokens.push({ text: chosen, kind: 'value' })
      }
      continue
    }

    // ── Interpolated value: {fieldId} ─────────────────────────────────────────
    const varMatch = segment.match(/^\{([^}]+)\}$/)
    if (varMatch) {
      const fieldId = varMatch[1]
      const field = fieldMap[fieldId]
      const rawValue = inputs[fieldId]

      if (!field) {
        tokens.push({ text: segment, kind: 'placeholder' })
        continue
      }

      if (isSensitiveField(field)) {
        tokens.push({ text: REDACTED_PLACEHOLDER, kind: 'redacted' })
        continue
      }

      const displayValue = redactValue(field, rawValue)
      if (!displayValue) {
        if (field.required) {
          tokens.push({ text: `<${field.label}>`, kind: 'missing' })
        }
        // optional empty → omit
        continue
      }
      tokens.push({ text: displayValue, kind: 'value' })
      continue
    }

    // ── Plain flag or binary name ─────────────────────────────────────────────
    if (segment.startsWith('-')) {
      tokens.push({ text: segment, kind: 'flag' })
    } else if (tokens.length === 0) {
      tokens.push({ text: segment, kind: 'command' })
    } else {
      tokens.push({ text: segment, kind: 'value' })
    }
  }

  return tokens
}

/** Render tokens to a plain string (for copy / aria-label). */
export function tokensToString(tokens: PreviewToken[]): string {
  return tokens.map((t) => t.text).join(' ')
}