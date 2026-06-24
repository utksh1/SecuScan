import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Reports from '../../../src/pages/Reports'
import { getReports, getDashboardSummary } from '../../../src/api'
import { isWithinDateRange } from '../../../src/utils/date'

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getDashboardSummary: vi.fn(),
  API_BASE: 'http://127.0.0.1:8000',
}))

const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

// Fixed base time so date-range tests are deterministic
const BASE_NOW = new Date('2026-05-14T12:00:00Z').getTime()

const readyReport = {
  id: 'report-1', task_id: 'task-abc-123',
  name: 'Security Scan — example.com', type: 'technical',
  generated_at: '2026-05-14T10:00:00Z', status: 'ready',
  findings: 7, assets: 3, pages: 12,
}
const newerReadyReport = {
  id: 'report-4', task_id: 'task-jkl-012',
  name: 'Security Scan — docs.example.com', type: 'technical',
  generated_at: '2026-05-14T11:30:00Z', status: 'ready',
  findings: 2, assets: 1, pages: 4,
}
const generatingReport = {
  id: 'report-2', task_id: 'task-def-456',
  name: 'Security Scan — staging.example.com', type: 'executive',
  generated_at: '2026-05-12T12:00:00Z', status: 'generating',
  findings: 0, assets: 0, pages: 0,
}
const failedReport = {
  id: 'report-3', task_id: 'task-ghi-789',
  name: 'Security Scan — api.example.com', type: 'compliance',
  generated_at: '2026-05-04T12:00:00Z', status: 'failed',
  findings: 0, assets: 0, pages: 0,
}
const emptySummary = {
  total_findings: 0, total_assets: 0, critical_findings: 0,
  high_findings: 0, total_attack_surface: 0,
}

function renderReports() {
  return render(<MemoryRouter><Reports /></MemoryRouter>)
}

// ── Loading state ─────────────────────────────────────────────────────────────────────────────

describe('Reports — loading state', () => {
  it('shows loading spinner while fetching', () => {
    vi.mocked(getReports).mockReturnValue(new Promise(() => {}))
    vi.mocked(getDashboardSummary).mockReturnValue(new Promise(() => {}))
    renderReports()
    expect(screen.getByText(/Retrieving Archive Data/i)).toBeInTheDocument()
  })
})

// ── Error state ───────────────────────────────────────────────────────────────────────────────

describe('Reports — error state', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockRejectedValue(new Error('Network error'))
    vi.mocked(getDashboardSummary).mockRejectedValue(new Error('Network error'))
    vi.mocked(getReports).mockClear()
  })

  it('shows error message when fetch fails', async () => {
    vi.mocked(getReports).mockRejectedValue(new Error('Network error'))
    vi.mocked(getDashboardSummary).mockRejectedValue(new Error('Network error'))
    renderReports()
    expect(await screen.findByText(/Archive_Retrieval_Failed/i)).toBeInTheDocument()
    expect(screen.getByText(/Failed to fetch reports/i)).toBeInTheDocument()
  })

  it('shows a retry button when fetch fails', async () => {
    vi.mocked(getReports).mockRejectedValue(new Error('Network error'))
    vi.mocked(getDashboardSummary).mockRejectedValue(new Error('Network error'))
    renderReports()
    expect(await screen.findByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('retries fetch when retry button is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(getReports).mockRejectedValue(new Error('Network error'))
    vi.mocked(getDashboardSummary).mockRejectedValue(new Error('Network error'))
    renderReports()
    await screen.findByRole('button', { name: /Retry/i })
    await user.click(screen.getByRole('button', { name: /Retry/i }))
    expect(vi.mocked(getReports)).toHaveBeenCalledTimes(2)
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────────────────────

describe('Reports — empty state', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
  })

  it('shows onboarding empty state when there are no reports at all', async () => {
    renderReports()
    expect(await screen.findByText(/No Briefings Yet/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /launch_first_scan/i })).toBeInTheDocument()
  })

  it('shows Archive Isolated when filter returns no matching reports', async () => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /executive briefings/i }))
    expect(await screen.findByText(/Archive Isolated/i)).toBeInTheDocument()
  })
})

// ── Export buttons — ready report ─────────────────────────────────────────────────────────────────

describe('Reports — export buttons on a ready report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('shows PDF, HTML and CSV buttons for a ready report', async () => {
    renderReports()
    expect(await screen.findByRole('button', { name: /^pdf$/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^html$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^csv$/i })).toBeInTheDocument()
  })

  it('export buttons are enabled for a ready report', async () => {
    renderReports()
    await screen.findByRole('button', { name: /^pdf$/ })
    expect(screen.getByRole('button', { name: /^pdf$/ })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).not.toBeDisabled()
  })

  it('clicking PDF opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()
    await user.click(await screen.findByRole('button', { name: /^pdf$/ }))
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/task/' + readyReport.task_id + '/report/pdf'), '_blank')
  })

  it('clicking HTML opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()
    await user.click(await screen.findByRole('button', { name: /^html$/i }))
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/task/' + readyReport.task_id + '/report/html'), '_blank')
  })

  it('clicking CSV opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()
    await user.click(await screen.findByRole('button', { name: /^csv$/i }))
    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/task/' + readyReport.task_id + '/report/csv'), '_blank')
  })

  it('does not use the old placeholder latest-report route', async () => {
    const user = userEvent.setup()
    renderReports()
    await user.click(await screen.findByRole('button', { name: /^pdf$/ }))
    expect(openSpy).not.toHaveBeenCalledWith(expect.stringContaining('latest'), expect.anything())
  })
})

describe('Reports — header export button', () => {
  beforeEach(() => {
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('opens the newest ready report PDF from the header button', async () => {
    const user = userEvent.setup()
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport, generatingReport, newerReadyReport, failedReport] })

    renderReports()

    await user.click(await screen.findByRole('button', { name: /download latest ready report pdf/i }))

    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining('/task/' + newerReadyReport.task_id + '/report/pdf'), '_blank')
    expect(openSpy).not.toHaveBeenCalledWith(expect.stringContaining('/task/latest/report/pdf'), expect.anything())
  })

  it('disables the header export button when there is no ready report', async () => {
    const user = userEvent.setup()
    vi.mocked(getReports).mockResolvedValue({ reports: [generatingReport, failedReport] })

    renderReports()

    const button = await screen.findByRole('button', { name: /download latest ready report pdf/i })
    expect(button).toBeDisabled()

    await user.click(button)
    expect(openSpy).not.toHaveBeenCalled()
  })
})

// ── Export buttons — generating report ────────────────────────────────────────────────────────────

describe('Reports — export buttons on a generating report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [generatingReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('export buttons are disabled when report is generating', async () => {
    renderReports()
    await screen.findByRole('button', { name: /^pdf$/ })
    expect(screen.getByRole('button', { name: /^pdf$/ })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).toBeDisabled()
  })

  it('clicking a disabled button does not open any URL', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByRole('button', { name: /^pdf$/ })
    await user.click(screen.getByRole('button', { name: /^pdf$/ }))
    expect(openSpy).not.toHaveBeenCalled()
  })
})

describe('Reports — export buttons on a failed report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [failedReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('export buttons are enabled for a failed report since backend supports it', async () => {
    renderReports()
    await screen.findByRole('button', { name: /^pdf$/ })
    expect(screen.getByRole('button', { name: /^pdf$/ })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).not.toBeDisabled()
  })
})

// ── Type filter ─────────────────────────────────────────────────────────────────────────────────────

describe('Reports — type filter', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport, generatingReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
  })

  it('shows all reports when All filter is selected', async () => {
    renderReports()
    expect(await screen.findByText(/Security Scan — example.com/i)).toBeInTheDocument()
    expect(screen.getByText(/Security Scan — staging.example.com/i)).toBeInTheDocument()
  })

  it('shows only matching reports when a type filter is selected', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /executive briefings/i }))
    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — example.com/i)).not.toBeInTheDocument()
    })
    expect(screen.getByText(/Security Scan — staging.example.com/i)).toBeInTheDocument()
  })
})

// ── Status filter ────────────────────────────────────────────────────────────────────────────────

describe('Reports — status filter', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport, generatingReport, failedReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
  })

  it('shows only ready reports when status filter is Ready', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /status ready/i }))
    expect(await screen.findByText(/Security Scan — example.com/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — staging.example.com/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Security Scan — api.example.com/i)).not.toBeInTheDocument()
    })
  })

  it('shows only failed reports when status filter is Failed', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /status failed/i }))
    expect(await screen.findByText(/Security Scan — api.example.com/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — example.com/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Security Scan — staging.example.com/i)).not.toBeInTheDocument()
    })
  })

  it('shows only generating reports when status filter is Generating', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /status generating/i }))
    expect(await screen.findByText(/Security Scan — staging.example.com/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — example.com/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Security Scan — api.example.com/i)).not.toBeInTheDocument()
    })
  })
})

// ── isWithinDateRange unit tests ──────────────────────────────────────────────────────────────────────

describe('isWithinDateRange', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(BASE_NOW))
  })
  afterEach(() => { vi.useRealTimers() })

  it('always returns true for range all', () => {
    expect(isWithinDateRange('2020-01-01T00:00:00Z', 'all')).toBe(true)
  })

  it('returns false for empty string', () => {
    expect(isWithinDateRange('', '24h')).toBe(false)
  })

  it('returns false for invalid date string', () => {
    expect(isWithinDateRange('not-a-date', '7d')).toBe(false)
  })

  it('matches a date 1 hour ago within 24h', () => {
    const d = new Date(BASE_NOW - 60 * 60 * 1000).toISOString()
    expect(isWithinDateRange(d, '24h')).toBe(true)
  })

  it('does not match a date 25 hours ago within 24h', () => {
    const d = new Date(BASE_NOW - 25 * 60 * 60 * 1000).toISOString()
    expect(isWithinDateRange(d, '24h')).toBe(false)
  })

  it('matches a date 2 days ago within 7d', () => {
    const d = new Date(BASE_NOW - 2 * 86400000).toISOString()
    expect(isWithinDateRange(d, '7d')).toBe(true)
  })

  it('does not match a date 8 days ago within 7d', () => {
    const d = new Date(BASE_NOW - 8 * 86400000).toISOString()
    expect(isWithinDateRange(d, '7d')).toBe(false)
  })

  it('matches a date 10 days ago within 30d', () => {
    const d = new Date(BASE_NOW - 10 * 86400000).toISOString()
    expect(isWithinDateRange(d, '30d')).toBe(true)
  })

  it('does not match a date 31 days ago within 30d', () => {
    const d = new Date(BASE_NOW - 31 * 86400000).toISOString()
    expect(isWithinDateRange(d, '30d')).toBe(false)
  })

  it('does not match a future date within 24h', () => {
    const d = new Date(BASE_NOW + 60 * 60 * 1000).toISOString()
    expect(isWithinDateRange(d, '24h')).toBe(false)
  })

  it('does not match a future date within 7d', () => {
    const d = new Date(BASE_NOW + 2 * 86400000).toISOString()
    expect(isWithinDateRange(d, '7d')).toBe(false)
  })
})

// ── Combined filters ─────────────────────────────────────────────────────────────────────────────────

describe('Reports — combined filters', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport, generatingReport, failedReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
  })

  it('type + status filter works correctly', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /technical/i }))
    await user.click(screen.getByRole('button', { name: /status ready/i }))
    expect(await screen.findByText(/Security Scan — example.com/i)).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — staging.example.com/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/Security Scan — api.example.com/i)).not.toBeInTheDocument()
    })
  })

  it('shows empty state when combined status + date filters match nothing', async () => {
    const user = userEvent.setup()
    renderReports()
    await screen.findByText(/Security Scan — example.com/i)
    await user.click(screen.getByRole('button', { name: /status failed/i }))
    await user.click(screen.getByRole('button', { name: /date last 24 hours/i }))
    expect(await screen.findByText(/archive isolated/i)).toBeInTheDocument()
  })
})
