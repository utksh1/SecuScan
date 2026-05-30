const SENSITIVE_PATTERNS = [
  /token=[^&\s]+/gi,
  /apikey=[^&\s]+/gi,
  /password=[^&\s]+/gi,
  /authorization:\s*bearer\s+[^\s]+/gi,
]

export type SanitizedError = {
  message: string
  stack?: string
}

function redactSensitiveData(value: string): string {
  let sanitized = value

  SENSITIVE_PATTERNS.forEach((pattern) => {
    sanitized = sanitized.replace(pattern, '[REDACTED]')
  })

  return sanitized
}

export function sanitizeError(error: Error): SanitizedError {
  const sanitizedMessage = redactSensitiveData(
    error.message || 'Unexpected error'
  )

  const sanitizedStack = redactSensitiveData(error.stack || '')

  return {
    message: sanitizedMessage,
    stack: sanitizedStack,
  }
}
