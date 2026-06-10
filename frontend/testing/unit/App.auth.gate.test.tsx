/**
 * App-level first-run auth gate tests (PR #278).
 *
 * The core reviewer requirement: once auth is enabled, the app must NOT let
 * any protected API call fire before the operator has provided the key.
 *
 * Covers:
 * - No key stored → setup screen is rendered; no fetch() is called.
 * - Saving a valid key → route tree replaces the setup screen.
 * - Saving an empty key → validation error; still on setup screen.
 * - Key already stored → app shell renders immediately; no setup screen.
 * - AUTH_REQUIRED_EVENT fired → setup screen re-appears; app shell hidden.
 * - New key saved after 401 → app shell returns; localStorage updated.
 */

import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// vi.mock calls are hoisted — all factories must be self-contained.
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'router' }, children),
  Routes: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'routes' }, children),
  Route: () => React.createElement('div', { 'data-testid': 'route' }),
  Navigate: () => React.createElement('div', { 'data-testid': 'navigate' }),
}))

vi.mock('../../src/components/AppShell', () => ({
  default: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'app-shell' }, children),
}))

vi.mock('../../src/pages/Dashboard', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-dashboard' }),
}))
vi.mock('../../src/pages/Toolkit', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-toolkit' }),
}))
vi.mock('../../src/pages/ToolConfig', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-toolconfig' }),
}))
vi.mock('../../src/pages/Findings', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-findings' }),
}))
vi.mock('../../src/pages/Reports', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-reports' }),
}))
vi.mock('../../src/pages/Settings', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-settings' }),
}))
vi.mock('../../src/pages/Scans', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-scans' }),
}))
vi.mock('../../src/pages/TaskDetails', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-taskdetails' }),
}))
vi.mock('../../src/pages/Workflows', () => ({
  default: () => React.createElement('div', { 'data-testid': 'page-workflows' }),
}))

import App from '../../src/App'
import { AUTH_REQUIRED_EVENT, setStoredApiKey } from '../../src/api'

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear()
  vi.unstubAllGlobals()
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  localStorage.clear()
})

// ---------------------------------------------------------------------------
// First-run: no key stored
// ---------------------------------------------------------------------------

describe('first-run gate (no key stored)', () => {
  it('renders the setup screen instead of the app routes', () => {
    const { container } = render(React.createElement(App))
    expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy()
    expect(container.querySelector('[data-testid="app-shell"]')).toBeNull()
  })

  it('does not call fetch() while the setup screen is showing', () => {
    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
    render(React.createElement(App))
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('shows the app shell after the operator saves a valid key', async () => {
    render(React.createElement(App))
    fireEvent.change(screen.getByLabelText(/Backend API Key/i), {
      target: { value: 'my-operator-key' },
    })
    fireEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() =>
      expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
    )
    expect(screen.getByTestId('app-shell')).toBeTruthy()
  })

  it('persists the key to localStorage after save', async () => {
    render(React.createElement(App))
    fireEvent.change(screen.getByLabelText(/Backend API Key/i), {
      target: { value: 'stored-key-abc' },
    })
    fireEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() =>
      expect(localStorage.getItem('secuscan_api_key')).toBe('stored-key-abc')
    )
  })

  it('shows a validation error and stays on setup screen for empty key', () => {
    render(React.createElement(App))
    fireEvent.click(screen.getByText(/Save and connect/i))
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy()
  })

  it('saves key on Enter keypress in the input', async () => {
    render(React.createElement(App))
    const input = screen.getByLabelText(/Backend API Key/i)
    fireEvent.change(input, { target: { value: 'enter-key-test' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    await waitFor(() =>
      expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
    )
    expect(localStorage.getItem('secuscan_api_key')).toBe('enter-key-test')
  })
})

// ---------------------------------------------------------------------------
// Key already stored: app renders normally
// ---------------------------------------------------------------------------

describe('key already stored', () => {
  it('renders the app shell without the setup screen', () => {
    setStoredApiKey('pre-seeded-key')
    render(React.createElement(App))
    expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
    expect(screen.getByTestId('app-shell')).toBeTruthy()
  })

  it('does not render the setup screen when a whitespace-trimmed key exists', () => {
    localStorage.setItem('secuscan_api_key', 'some-valid-key')
    render(React.createElement(App))
    expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// 401 re-triggers the gate
// ---------------------------------------------------------------------------

describe('401 re-triggers setup screen', () => {
  it('shows the setup screen when AUTH_REQUIRED_EVENT fires', async () => {
    setStoredApiKey('valid-key')
    render(React.createElement(App))
    expect(screen.getByTestId('app-shell')).toBeTruthy()

    act(() => { window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT)) })

    await waitFor(() =>
      expect(screen.getByRole('main', { name: /api key setup/i })).toBeTruthy()
    )
    expect(screen.queryByTestId('app-shell')).toBeNull()
  })

  it('hides the setup screen after a new key is saved post-401', async () => {
    setStoredApiKey('valid-key')
    render(React.createElement(App))
    act(() => { window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT)) })
    await waitFor(() => screen.getByRole('main', { name: /api key setup/i }))

    fireEvent.change(screen.getByLabelText(/Backend API Key/i), {
      target: { value: 'new-key-after-401' },
    })
    fireEvent.click(screen.getByText(/Save and connect/i))

    await waitFor(() =>
      expect(screen.queryByRole('main', { name: /api key setup/i })).toBeNull()
    )
    expect(screen.getByTestId('app-shell')).toBeTruthy()
    expect(localStorage.getItem('secuscan_api_key')).toBe('new-key-after-401')
  })

  it('does not call fetch() after 401 until the new key is saved', async () => {
    setStoredApiKey('old-key')
    render(React.createElement(App))

    const fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)

    act(() => { window.dispatchEvent(new CustomEvent(AUTH_REQUIRED_EVENT)) })
    await waitFor(() => screen.getByRole('main', { name: /api key setup/i }))

    // The app shell is gone — no components that would call fetch are mounted.
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
