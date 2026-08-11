

export type ValidationTypeName = 'url' | 'hostname' | 'domain' | 'ipv4' | 'port' | 'cidr'

export interface FieldValidation {
  pattern?: string
  message?: string
  min?: number
  max?: number
  validation_type?: ValidationTypeName
}

interface ValidationPreset {
  pattern: RegExp
  message: string
}

const VALIDATION_PRESETS: Record<ValidationTypeName, ValidationPreset> = {
  url: {
    pattern: /^https?:\/\/[^\s/$.?#].[^\s]*$/i,
    message: 'Must be a valid URL starting with http:// or https://',
  },
  hostname: {
    pattern: /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/,
    message: 'Must be a valid hostname (e.g. example.com or sub.example.com)',
  },
  domain: {
    pattern: /^(?!https?:\/\/)(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$/,
    message: 'Must be a valid domain name without a scheme (e.g. example.com)',
  },
  ipv4: {
    pattern: /^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)$/,
    message: 'Must be a valid IPv4 address (e.g. 192.168.1.1)',
  },
  port: {
    pattern: /^(6553[0-5]|655[0-2]\d|65[0-4]\d{2}|6[0-4]\d{3}|[1-5]\d{4}|[1-9]\d{0,3}|[1-9])$/,
    message: 'Must be a valid port number between 1 and 65535',
  },
  cidr: {
    pattern: /^(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)(\.(25[0-5]|2[0-4]\d|1\d{2}|[1-9]\d|\d)){3}\/(3[0-2]|[12]\d|[0-9])$/,
    message: 'Must be a valid CIDR block (e.g. 192.168.1.0/24)',
  },
}


export function getValidationError(
  field: {
    id: string
    label: string
    type: string
    required?: boolean
    validation?: Record<string, unknown>
  },
  value: unknown,
): string | null {
  if (field.required) {
    if (value === undefined || value === null) return `${field.label} is required`
    if (typeof value === 'string' && value.trim().length === 0) return `${field.label} is required`
    if (Array.isArray(value) && value.length === 0) return `${field.label} is required`
  }

  const validation = (field.validation ?? {}) as FieldValidation
  const customMessage = validation.message ?? null

  if (typeof value === 'string' && value.trim().length > 0) {
    const trimmed = value.trim()

    const typeName = validation.validation_type
    if (typeName && VALIDATION_PRESETS[typeName]) {
      const preset = VALIDATION_PRESETS[typeName]
      if (!preset.pattern.test(trimmed)) {
        return customMessage ?? preset.message
      }
      return null
    }

    const rawPattern = validation.pattern
    if (typeof rawPattern === 'string') {
      try {
        if (!new RegExp(rawPattern).test(trimmed)) {
          return customMessage ?? `${field.label} is not valid`
        }
      } catch {
      }
    }
  }

  if (field.type === 'integer' && value !== '' && value !== undefined && value !== null) {
    const num = typeof value === 'number' ? value : Number(value)
    if (!Number.isFinite(num) || !Number.isInteger(num)) {
      return customMessage ?? `${field.label} must be a whole number`
    }
    const min = typeof validation.min === 'number' ? validation.min : null
    const max = typeof validation.max === 'number' ? validation.max : null
    if (min !== null && num < min) return customMessage ?? `${field.label} must be at least ${min}`
    if (max !== null && num > max) return customMessage ?? `${field.label} must be no more than ${max}`
  }

  return null
}


export function isFormValid(
  fields: Array<{ id: string; label: string; type: string; required?: boolean; validation?: Record<string, unknown> }>,
  inputs: Record<string, unknown>,
): boolean {
  return fields.every((field) => getValidationError(field, inputs[field.id]) === null)
}