import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'

vi.mock('../../../src/api', () => ({
  checkAuthSession: vi.fn(),
  logoutSession: vi.fn(),
  authenticateWithApiKey: vi.fn(),
  AUTH_REQUIRED_EVENT: 'secuscan:auth-required',
}))

import SignIn from '../../../src/pages/SignIn'
import { AuthProvider } from '../../../src/components/AuthContext'
import { checkAuthSession, authenticateWithApiKey } from '../../../src/api'

function renderSignIn(entry: any = '/signin') {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[entry]}>
        <Routes>
          <Route path="/signin" element={<SignIn />} />
          <Route path="/" element={<div>DASHBOARD HOME</div>} />
          <Route path="/findings" element={<div>FINDINGS PAGE</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

describe('SignIn page (issue #795)', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockReset().mockResolvedValue(false)
    vi.mocked(authenticateWithApiKey).mockReset()
  })

  it('renders the real API-key entry', async () => {
    renderSignIn()
    expect(await screen.findByRole('main', { name: /api key setup/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/Backend API Key/i)).toBeInTheDocument()
  })

  it('authenticates against the backend and redirects to the dashboard', async () => {
    vi.mocked(authenticateWithApiKey).mockResolvedValue(undefined)
    renderSignIn()
    await screen.findByLabelText(/Backend API Key/i)

    await userEvent.type(screen.getByLabelText(/Backend API Key/i), 'operator-key-123')
    await userEvent.click(screen.getByText(/Save and connect/i))

    expect(authenticateWithApiKey).toHaveBeenCalledWith('operator-key-123')
    await waitFor(() => expect(screen.getByText('DASHBOARD HOME')).toBeInTheDocument())
  })

  it('returns the operator to the route they were redirected from', async () => {
    vi.mocked(authenticateWithApiKey).mockResolvedValue(undefined)
    renderSignIn({ pathname: '/signin', state: { from: { pathname: '/findings' } } })
    await screen.findByLabelText(/Backend API Key/i)

    await userEvent.type(screen.getByLabelText(/Backend API Key/i), 'operator-key-123')
    await userEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() => expect(screen.getByText('FINDINGS PAGE')).toBeInTheDocument())
  })

  it('shows the backend error and does not redirect when the key is rejected', async () => {
    vi.mocked(authenticateWithApiKey).mockRejectedValue(new Error('Invalid API key'))
    renderSignIn()
    await screen.findByLabelText(/Backend API Key/i)

    await userEvent.type(screen.getByLabelText(/Backend API Key/i), 'wrong-key')
    await userEvent.click(screen.getByText(/Save and connect/i))

    expect(await screen.findByRole('alert')).toHaveTextContent(/invalid api key/i)
    expect(screen.queryByText('DASHBOARD HOME')).not.toBeInTheDocument()
  })

  it('redirects away if a session already exists', async () => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    renderSignIn()
    await waitFor(() => expect(screen.getByText('DASHBOARD HOME')).toBeInTheDocument())
    expect(authenticateWithApiKey).not.toHaveBeenCalled()
  })
})
