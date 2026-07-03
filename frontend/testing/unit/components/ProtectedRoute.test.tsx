import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../../../src/api', () => ({
  checkAuthSession: vi.fn(),
  logoutSession: vi.fn(),
  authenticateWithApiKey: vi.fn(),
  AUTH_REQUIRED_EVENT: 'secuscan:auth-required',
}))

import ProtectedRoute from '../../../src/components/ProtectedRoute'
import { AuthProvider } from '../../../src/components/AuthContext'
import { checkAuthSession } from '../../../src/api'

function renderAt(initialPath: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/secret" element={<div>SECRET WORKSPACE</div>} />
          </Route>
          <Route path="/signin" element={<div>SIGN IN PAGE</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

describe('ProtectedRoute (issue #795)', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockReset()
  })

  it('redirects to sign-in when the backend reports no session', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(false)
    renderAt('/secret')
    await waitFor(() => expect(screen.getByText('SIGN IN PAGE')).toBeInTheDocument())
    expect(screen.queryByText('SECRET WORKSPACE')).not.toBeInTheDocument()
  })

  it('renders the protected content when the backend confirms a session', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    renderAt('/secret')
    await waitFor(() => expect(screen.getByText('SECRET WORKSPACE')).toBeInTheDocument())
    expect(screen.queryByText('SIGN IN PAGE')).not.toBeInTheDocument()
  })

  it('does not mount protected content while the session check is in flight', async () => {
    // A never-resolving check keeps the guard in its loading state.
    vi.mocked(checkAuthSession).mockReturnValue(new Promise(() => {}))
    renderAt('/secret')
    // Neither the protected content nor a premature redirect appears.
    expect(screen.queryByText('SECRET WORKSPACE')).not.toBeInTheDocument()
    expect(screen.queryByText('SIGN IN PAGE')).not.toBeInTheDocument()
  })
})
