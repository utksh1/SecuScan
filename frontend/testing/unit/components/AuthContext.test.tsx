import React from 'react'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock only the network boundary; the auth code path under test is real.
vi.mock('../../../src/api', () => ({
  checkAuthSession: vi.fn(),
  logoutSession: vi.fn(),
  authenticateWithApiKey: vi.fn(),
  AUTH_REQUIRED_EVENT: 'secuscan:auth-required',
}))

import { AuthProvider, useAuth } from '../../../src/components/AuthContext'
import { checkAuthSession, logoutSession, AUTH_REQUIRED_EVENT } from '../../../src/api'

function Harness() {
  const { isAuthenticated, loading, markAuthenticated, signOut } = useAuth()
  return (
    <div>
      <div data-testid="status">{loading ? 'loading' : isAuthenticated ? 'in' : 'out'}</div>
      <button onClick={() => markAuthenticated()}>mark</button>
      <button onClick={() => signOut()}>signout</button>
    </div>
  )
}

function renderHarness() {
  return render(
    <AuthProvider>
      <Harness />
    </AuthProvider>,
  )
}

describe('AuthContext (issue #795)', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockReset()
    vi.mocked(logoutSession).mockReset()
  })

  it('derives an authenticated state from the backend session check', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    renderHarness()
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('in'))
    expect(checkAuthSession).toHaveBeenCalledTimes(1)
  })

  it('is signed out when the backend reports no session', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(false)
    renderHarness()
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('out'))
  })

  it('drops to signed out when AUTH_REQUIRED_EVENT fires (a 401 elsewhere)', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    renderHarness()
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('in'))

    act(() => {
      window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT))
    })
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('out'))
  })

  it('signOut calls the backend logout endpoint and clears the session', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    vi.mocked(logoutSession).mockResolvedValue(undefined)
    renderHarness()
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('in'))

    await userEvent.click(screen.getByText('signout'))
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('out'))
    expect(logoutSession).toHaveBeenCalledTimes(1)
  })

  it('markAuthenticated flips to signed in after a verified key sign-in', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(false)
    renderHarness()
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('out'))

    await userEvent.click(screen.getByText('mark'))
    await waitFor(() => expect(screen.getByTestId('status')).toHaveTextContent('in'))
  })
})
