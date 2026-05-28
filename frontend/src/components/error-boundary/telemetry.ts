import type { SanitizedError } from './sanitizeError'

export type TelemetryPayload = SanitizedError & {
  componentStack?: string
  route?: string
}

export function captureError(payload: TelemetryPayload) {
  if (import.meta.env.DEV) {
    console.error('[Frontend Telemetry]', {
      message: payload.message,
      stack: payload.stack,
      componentStack: payload.componentStack,
      route: payload.route,
    })
  }

  // future telemetry integrations
}
