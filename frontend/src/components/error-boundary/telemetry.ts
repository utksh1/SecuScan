import type { SanitizedError } from './sanitizeError'

export type TelemetryPayload = SanitizedError & {
  componentStack?: string | null
  route?: string
}

export interface TelemetryAdapter {
  capture(payload: TelemetryPayload): void
}

const noopAdapter: TelemetryAdapter = {
  capture: () => {},
}

let activeAdapter: TelemetryAdapter = noopAdapter

export function setTelemetryAdapter(adapter: TelemetryAdapter): void {
  activeAdapter = adapter
}

export function captureError(payload: TelemetryPayload): void {
  if (import.meta.env.DEV) {
    console.error('[Frontend Telemetry]', {
      message: payload.message,
      stack: payload.stack,
      componentStack: payload.componentStack,
      route: payload.route,
    })
  }
  activeAdapter.capture(payload)
}
