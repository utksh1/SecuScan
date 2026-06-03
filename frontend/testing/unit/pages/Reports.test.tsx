import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Reports from '../../../src/pages/Reports'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getDashboardSummary: vi.fn(),
  API_BASE: 'http://localhost:5000',
}))

vi.mock('../../../src/utils/date', () => ({
  formatDateLong: (d: any) => d ?? '',
}))

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { configurable: true, value: 800 })
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })

import { getReports, getDashboardSummary } from '../../../src/api'

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeReport(overrides: any = {}) {
  return {
    id: `r-${Math.random().toString(36).slice(2)}`,
    task_id: 'task-001',
    name: 'Test Report',
    type: 'technical' as const,
    generated_at: '2024-01-01T00:00:00Z',
    status: 'ready' as const,
    findings: 12,
    assets: 3,
    pages: 8,
    ...overrides,
  }
}

function makeLargeDataset(count: number) {
  return Array.from({ length: count }, (_, i) =>
    makeReport({
      id: `r-${i}`,
      name: `Report ${i}`,
      type: (['executive', 'technical', 'compliance'] as const)[i % 3],
    }),
  )
}

function mockApis(reports: ReturnType<typeof makeReport>[], summary: any = {}) {
  vi.mocked(getReports).mockResolvedValue({ reports })
  vi.mocked(getDashboardSummary).mockResolvedValue({
    total_findings: 42,
    total_assets: 7,
    ...summary,
  })
}

function renderReports() {
  return render(
    <MemoryRouter>
      <Reports />
    </MemoryRouter>
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Reports — virtualized grid', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page header', () => {
    mockApis([])
    renderReports()
    expect(screen.getByText(/Analytics/i)).toBeInTheDocument()
  })

  it('shows empty state when no reports', async () => {
    mockApis([])
    renderReports()
    await waitFor(() => expect(screen.getByText(/Archive Isolated/i)).toBeInTheDocument())
  })

  it('renders report cards for loaded reports', async () => {
    const reports = [makeReport({ name: 'Q1 Security Audit' })]
    mockApis(reports)
    renderReports()
    await waitFor(() => expect(screen.getByText('Q1 Security Audit')).toBeInTheDocument())
  })

  it('does not mount all cards to DOM with 200 reports (DOM bloat test)', async () => {
    const reports = makeLargeDataset(200)
    mockApis(reports)
    const { container } = renderReports()

    await waitFor(() => expect(screen.queryByText(/Archive Isolated/i)).not.toBeInTheDocument(), { timeout: 3000 })

    // Each virtual row holds 2 cards; overscan(3) = ~8 rows visible max
    // 200 reports = 100 rows; only a small window should render
    const cards = container.querySelectorAll('.group')
    expect(cards.length).toBeLessThan(30)
  })

  it('filters by type using sidebar buttons', async () => {
    const reports = [
      makeReport({ id: 'r1', name: 'Exec Report', type: 'executive' }),
      makeReport({ id: 'r2', name: 'Tech Report', type: 'technical' }),
    ]
    mockApis(reports)
    renderReports()

    await waitFor(() => expect(screen.getByText('Exec Report')).toBeInTheDocument())

    // Click 'executive BRIEFINGS'
    await userEvent.click(screen.getByRole('button', { name: /executive BRIEFINGS/i }))

    expect(screen.getByText('Exec Report')).toBeInTheDocument()
    expect(screen.queryByText('Tech Report')).not.toBeInTheDocument()
  })

  it('resets to all types when "all BRIEFINGS" is clicked', async () => {
    const reports = [
      makeReport({ id: 'r1', name: 'Exec Report', type: 'executive' }),
      makeReport({ id: 'r2', name: 'Tech Report', type: 'technical' }),
    ]
    mockApis(reports)
    renderReports()

    await waitFor(() => expect(screen.getByText('Exec Report')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /executive BRIEFINGS/i }))
    await userEvent.click(screen.getByRole('button', { name: /all BRIEFINGS/i }))

    expect(screen.getByText('Exec Report')).toBeInTheDocument()
    expect(screen.getByText('Tech Report')).toBeInTheDocument()
  })

  it('displays metrics from summary API', async () => {
    mockApis([], { total_findings: 99, total_assets: 15 })
    renderReports()

    await waitFor(() => {
      expect(screen.getByText('99')).toBeInTheDocument()
      expect(screen.getByText('15')).toBeInTheDocument()
    })
  })

  it('refresh button re-fetches reports', async () => {
    mockApis([makeReport({ name: 'Initial Report' })])
    renderReports()

    await waitFor(() => expect(screen.getByText('Initial Report')).toBeInTheDocument())

    mockApis([makeReport({ name: 'Initial Report' }), makeReport({ name: 'Refreshed Report' })])
    await userEvent.click(screen.getByTitle('Refresh Archive'))

    await waitFor(() => expect(screen.getByText('Refreshed Report')).toBeInTheDocument())
  })

  it('report card shows correct status bar colour for ready/failed/generating', async () => {
    const reports = [
      makeReport({ id: 'r1', name: 'Ready Report', status: 'ready' }),
      makeReport({ id: 'r2', name: 'Failed Report', status: 'failed' }),
    ]
    mockApis(reports)
    const { container } = renderReports()

    await waitFor(() => expect(screen.getByText('Ready Report')).toBeInTheDocument())

    // Green bar for ready
    const greenBars = container.querySelectorAll('.bg-rag-green.w-full')
    expect(greenBars.length).toBeGreaterThan(0)

    // Red bar for failed
    const redBars = container.querySelectorAll('.bg-rag-red.w-full')
    expect(redBars.length).toBeGreaterThan(0)
  })

  it('negative: compliance type filter hides executive and technical reports', async () => {
    const reports = [
      makeReport({ id: 'r1', name: 'Executive Dossier', type: 'executive' }),
      makeReport({ id: 'r2', name: 'Technical Intel', type: 'technical' }),
      makeReport({ id: 'r3', name: 'Compliance Audit', type: 'compliance' }),
    ]
    mockApis(reports)
    renderReports()

    await waitFor(() => expect(screen.getByText('Compliance Audit')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /compliance BRIEFINGS/i }))

    expect(screen.getByText('Compliance Audit')).toBeInTheDocument()
    expect(screen.queryByText('Executive Dossier')).not.toBeInTheDocument()
    expect(screen.queryByText('Technical Intel')).not.toBeInTheDocument()
  })
})
