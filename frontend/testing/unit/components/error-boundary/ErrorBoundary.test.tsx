import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

import ErrorBoundary from '../../../../src/components/error-boundary/ErrorBoundary'
import { sanitizeError } from '../../../../src/components/error-boundary/sanitizeError'
function BrokenComponent(): JSX.Element {
  throw new Error('token=123456')
}

function HealthyComponent() {
  return <div>Healthy Component</div>
}

describe('ErrorBoundary', () => {
  it('renders fallback UI on error', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      </MemoryRouter>
    )

    expect(
      screen.getByText(/something went wrong/i)
    ).toBeInTheDocument()
  })

  it('renders healthy component without crashing', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <HealthyComponent />
        </ErrorBoundary>
      </MemoryRouter>
    )

    expect(
      screen.getByText(/healthy component/i)
    ).toBeInTheDocument()
  })

  it('redacts sensitive information', () => {
    const error = new Error('token=123456')

    error.stack = 'authorization: bearer SECRET_TOKEN'

    const sanitized = sanitizeError(error)

    expect(sanitized.stack).not.toContain('SECRET_TOKEN')

    expect(sanitized.stack).toContain('[REDACTED]')
  })

  it('shows retry button', () => {
    render(
      <MemoryRouter>
        <ErrorBoundary>
          <BrokenComponent />
        </ErrorBoundary>
      </MemoryRouter>
    )

    expect(
      screen.getByRole('button', { name: /retry/i })
    ).toBeInTheDocument()
  })
})