import React from 'react'
import ErrorFallback from './ErrorFallback'
import { sanitizeError } from './sanitizeError'
import { captureError } from './telemetry'

type Props = {
  children: React.ReactNode
}

type State = {
  hasError: boolean
  error?: Error
  sanitizedMessage?: string
}

class ErrorBoundary extends React.Component<Props, State> {
  state: State = {
    hasError: false,
  }

  static getDerivedStateFromError(error: Error): State {
    const sanitized = sanitizeError(error)
    return {
      hasError: true,
      error,
      sanitizedMessage: sanitized.message ?? undefined,
    }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    const sanitized = sanitizeError(error)
    captureError({
      ...sanitized,
      componentStack: info.componentStack,
    })
  }

  resetBoundary = () => {
    this.setState({
      hasError: false,
      error: undefined,
      sanitizedMessage: undefined,
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <ErrorFallback
          errorMessage={this.state.sanitizedMessage}
          onRetry={this.resetBoundary}
        />
      )
    }
    return this.props.children
  }
}

export default ErrorBoundary
