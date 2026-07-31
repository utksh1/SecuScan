import { render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import { beforeEach, describe, it, expect, vi } from 'vitest'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { AppRoutes } from '../../src/App'
import { ThemeProvider } from '../../src/components/ThemeContext'
import { AuthProvider } from '../../src/components/AuthContext'

// Keep AppRoutes a focused routing test: stub the shell, mock the network.
vi.mock('../../src/components/AppShell', () => ({
  default: ({ children }: { children: React.ReactNode }) =>
    React.createElement('div', { 'data-testid': 'app-shell' }, children),
}))

vi.mock('../../src/api', () => ({
  // Authenticated session so the protected route tree renders.
  checkAuthSession: vi.fn().mockResolvedValue(true),
  logoutSession: vi.fn(),
  authenticateWithApiKey: vi.fn(),
  AUTH_REQUIRED_EVENT: 'secuscan:auth-required',
  getHealth: vi.fn().mockResolvedValue({ status: 'operational' }),
  getDashboardSummary: vi.fn().mockResolvedValue({
    total_findings: 0,
    critical_findings: 0,
    high_findings: 0,
    medium_findings: 0,
    low_findings: 0,
    info_findings: 0,
    last_scan_time: null,
    recent_findings: [],
    running_tasks: [],
    recent_tasks: [],
    scan_activity: { total: 0, completed: 0, running: 0 },
  }),
  getFindings: vi.fn().mockResolvedValue({
    findings: [
      {
        id: 'finding-1',
        severity: 'high',
        category: 'Web',
        title: 'Open Admin Surface',
        target: 'app.example.test',
        description: 'Administrative endpoint is reachable from the public network.',
        remediation: 'Restrict access using authentication and IP controls.',
        discovered_at: '2026-05-07T06:00:00Z',
        cve: null,
      },
    ],
  }),
  cancelTask: vi.fn(),
}))

function PathProbe() {
  const { pathname } = useLocation()
  return <div data-testid="path-probe">{pathname}</div>
}

function renderAt(path: string, extra?: React.ReactNode) {
  return render(
    <ThemeProvider>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <AppRoutes />
          {extra}
        </MemoryRouter>
      </AuthProvider>
    </ThemeProvider>,
  )
}

describe('App route fallback (authenticated)', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('renders NotFound page for unknown routes', async () => {
    renderAt('/not-a-real-route', <PathProbe />)
    await waitFor(() => {
      expect(screen.getByTestId('path-probe')).toHaveTextContent('/not-a-real-route')
    })
    expect(await screen.findByText(/Perimeter Breach/i)).toBeInTheDocument()
  })

  it('renders the loaded dashboard summary', async () => {
    renderAt('/')
    expect(await screen.findByText(/Total Findings/i)).toBeInTheDocument()
    expect(screen.getByText(/Scan Cycles/i)).toBeInTheDocument()
  })

  it('renders the findings workspace', async () => {
    renderAt('/findings')
    expect(await screen.findByRole('heading', { name: /Findings/i })).toBeInTheDocument()
  })
})
