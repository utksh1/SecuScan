import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { AppRoutes } from './App'

vi.mock('./api', () => ({
  getHealth: vi.fn().mockResolvedValue({ status: 'operational' }),
  getDashboardSummary: vi.fn().mockResolvedValue({
    total_assets: 0,
    active_assets: 0,
    critical_assets: 0,
    total_attack_surface: 0,
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
    has_high_risk_assets: false,
    high_risk_assets: [],
    attack_surface_by_category: {},
    scan_activity: { total: 0, completed: 0, running: 0 },
  }),
  cancelTask: vi.fn(),
}))

function PathProbe() {
  const { pathname } = useLocation()
  return <div data-testid="path-probe">{pathname}</div>
}

describe('App route fallback', () => {
  it('redirects unknown routes to dashboard', async () => {
    render(
      <MemoryRouter initialEntries={['/not-a-real-route']}>
        <AppRoutes />
        <PathProbe />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('path-probe')).toHaveTextContent('/')
    })
  })
})
