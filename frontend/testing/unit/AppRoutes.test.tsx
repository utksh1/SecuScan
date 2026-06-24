import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { AppRoutes } from '../../src/App'
import { ThemeProvider } from '../../src/components/ThemeContext'

vi.mock('../../src/api', () => ({
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

describe('App route fallback', () => {
  it('renders NotFound page for unknown routes', async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={['/not-a-real-route']}>
          <AppRoutes />
          <PathProbe />
        </MemoryRouter>
      </ThemeProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('path-probe')).toHaveTextContent('/not-a-real-route')
    })
    expect(screen.getByText(/Perimeter Breach/i)).toBeInTheDocument()
  })

  it('renders the loaded dashboard summary', async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={['/']}>
          <AppRoutes />
        </MemoryRouter>
      </ThemeProvider>,
    )

    expect(await screen.findByText(/Total Findings/i)).toBeInTheDocument()
    expect(screen.getByText(/Scan Cycles/i)).toBeInTheDocument()
  })

  it('renders the findings workspace', async () => {
    render(
      <ThemeProvider>
        <MemoryRouter initialEntries={['/findings']}>
          <AppRoutes />
        </MemoryRouter>
      </ThemeProvider>,
    )

    expect(await screen.findByRole('heading', { name: /Findings/i })).toBeInTheDocument()
  })
})
