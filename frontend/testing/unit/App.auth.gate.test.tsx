/**
 * App-level auth gate tests.
 *
 * Core security requirement (unchanged): no protected page — and therefore no
 * protected API call — may mount before the operator has a valid backend
 * session. Gating is now expressed through the real ProtectedRoute + the real
 * API-key sign-in (ApiKeySetupScreen → authenticateWithApiKey), so these tests
 * drive AppRoutes through a real router with only the network boundary mocked.
 *
 * Covers:
 * - No session → API-key sign-in shown; no page mounts; no fetch fires.
 * - Saving a valid key → app shell + page render.
 * - Saving an empty key → validation error; still on sign-in.
 * - Session already established → app renders immediately.
 * - AUTH_REQUIRED_EVENT (401) → sign-in returns; app hidden; no fetch.
 * - New key after 401 → app returns.
 * - Enter key submits.
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../../src/components/AppShell', () => ({
  default: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'app-shell' }, children),
}))

vi.mock('../../src/pages/Dashboard', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-dashboard' }),
}))
vi.mock('../../src/pages/Toolkit', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/ToolConfig', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/Findings', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/Reports', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/ReportCompare', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/Settings', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/Scans', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/TaskDetails', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/Workflows', () => ({ default: () => React.createElement('div') }))
vi.mock('../../src/pages/NotFound', () => ({ default: () => React.createElement('div') }))

vi.mock('../../src/api', () => ({
  checkAuthSession: vi.fn(),
  authenticateWithApiKey: vi.fn(),
  logoutSession: vi.fn(),
  AUTH_REQUIRED_EVENT: 'secuscan:auth-required',
}))

import { AppRoutes } from '../../src/App'
import { AuthProvider } from '../../src/components/AuthContext'
import { checkAuthSession, authenticateWithApiKey, AUTH_REQUIRED_EVENT } from '../../src/api'

function renderApp() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={['/']}>
        <AppRoutes />
      </MemoryRouter>
    </AuthProvider>,
  )
}

beforeEach(() => {
  vi.unstubAllGlobals()
  vi.mocked(checkAuthSession).mockReset()
  vi.mocked(authenticateWithApiKey).mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('first-run gate (no session)', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockResolvedValue(false)
    vi.mocked(authenticateWithApiKey).mockResolvedValue(undefined)
  })

  it('shows the API-key sign-in instead of the app, and no page mounts', async () => {
    renderApp()
    await waitFor(() =>
      expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy(),
    )
    expect(screen.queryByTestId('app-shell')).toBeNull()
    expect(screen.queryByTestId('page-dashboard')).toBeNull()
  })

  it('does not call fetch() while the sign-in screen is showing', async () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    renderApp()
    await waitFor(() =>
      expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy(),
    )
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('shows the app after the operator saves a valid key', async () => {
    renderApp()
    await screen.findByLabelText(/Backend API Key/i)

    fireEvent.change(screen.getByLabelText(/Backend API Key/i), {
      target: { value: 'my-operator-key' },
    })
    fireEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())
    expect(screen.getByTestId('page-dashboard')).toBeTruthy()
    expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
    expect(authenticateWithApiKey).toHaveBeenCalledWith('my-operator-key')
  })

  it('shows a validation error and stays on sign-in for an empty key', async () => {
    renderApp()
    await screen.findByLabelText(/Backend API Key/i)

    fireEvent.click(screen.getByText(/Save and connect/i))
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy()
    expect(authenticateWithApiKey).not.toHaveBeenCalled()
  })

  it('submits the key on Enter', async () => {
    renderApp()
    await screen.findByLabelText(/Backend API Key/i)

    const input = screen.getByLabelText(/Backend API Key/i)
    fireEvent.change(input, { target: { value: 'enter-key-test' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())
    expect(authenticateWithApiKey).toHaveBeenCalledWith('enter-key-test')
  })
})

describe('session already established', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
  })

  it('renders the app without the sign-in screen', async () => {
    renderApp()
    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())
    expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
  })
})

describe('401 re-triggers the sign-in screen', () => {
  beforeEach(() => {
    vi.mocked(checkAuthSession).mockResolvedValue(true)
    vi.mocked(authenticateWithApiKey).mockResolvedValue(undefined)
  })

  it('shows the sign-in screen when AUTH_REQUIRED_EVENT fires', async () => {
    renderApp()
    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())

    act(() => {
      window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT))
    })

    await waitFor(() =>
      expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy(),
    )
    expect(screen.queryByTestId('app-shell')).toBeNull()
  })

  it('returns to the app after a new key is saved post-401', async () => {
    renderApp()
    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())

    act(() => {
      window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT))
    })
    await screen.findByLabelText(/Backend API Key/i)

    fireEvent.change(screen.getByLabelText(/Backend API Key/i), {
      target: { value: 'new-key-after-401' },
    })
    fireEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() => expect(screen.getByTestId('app-shell')).toBeTruthy())
    expect(authenticateWithApiKey).toHaveBeenCalledWith('new-key-after-401')
  })
})
