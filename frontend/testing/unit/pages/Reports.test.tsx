import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Reports from '../../../src/pages/Reports'
import { getReports, getDashboardSummary } from '../../../src/api'

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getDashboardSummary: vi.fn(),
  API_BASE: 'http://127.0.0.1:8000',
}))

// Stops "window.open is not a function" errors in the test environment
const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

// ── Shared fixtures ───────────────────────────────────────────────────────────

const readyReport = {
  id: 'report-1',
  task_id: 'task-abc-123',
  name: 'Security Scan — example.com',
  type: 'technical',
  generated_at: '2026-05-14T10:00:00Z',
  status: 'ready',
  findings: 7,
  assets: 3,
  pages: 12,
}

const generatingReport = {
  id: 'report-2',
  task_id: 'task-def-456',
  name: 'Security Scan — staging.example.com',
  type: 'executive',
  generated_at: '2026-05-14T11:00:00Z',
  status: 'generating',
  findings: 0,
  assets: 0,
  pages: 0,
}

const failedReport = {
  id: 'report-3',
  task_id: 'task-ghi-789',
  name: 'Security Scan — api.example.com',
  type: 'compliance',
  generated_at: '2026-05-14T12:00:00Z',
  status: 'failed',
  findings: 0,
  assets: 0,
  pages: 0,
}

const emptySummary = {
  total_findings: 0,
  total_assets: 0,
  critical_findings: 0,
  high_findings: 0,
  total_attack_surface: 0,
}

// ── Helper ────────────────────────────────────────────────────────────────────

function renderReports() {
  return render(
    <MemoryRouter>
      <Reports />
    </MemoryRouter>,
  )
}

// ── Loading state ─────────────────────────────────────────────────────────────

describe('Reports — loading state', () => {
  
  it('shows loading spinner while fetching', () => {
    // Never resolves so the loading state stays visible
    vi.mocked(getReports).mockReturnValue(new Promise(() => {}))
    vi.mocked(getDashboardSummary).mockReturnValue(new Promise(() => {}))

    renderReports()

    expect(screen.getByText(/Retrieving Archive Data/i)).toBeInTheDocument()
  })
})

// ── Error state ───────────────────────────────────────────────────────────────

describe('Reports — error state', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockRejectedValue(new Error('Network error'))
    vi.mocked(getDashboardSummary).mockRejectedValue(new Error('Network error'))
    vi.mocked(getReports).mockClear()  // ← reset call count before each test
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

    // getReports should have been called twice — once on load, once on retry
    expect(vi.mocked(getReports)).toHaveBeenCalledTimes(2)
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────

describe('Reports — empty state', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
  })

  it('shows Archive Isolated when there are no reports at all', async () => {
    renderReports()
    expect(await screen.findByText(/Archive Isolated/i)).toBeInTheDocument()
  })

  it('shows Archive Isolated when filter returns no matching reports', async () => {
    // Only a technical report exists
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
    const user = userEvent.setup()

    renderReports()

    await screen.findByText(/Security Scan — example.com/i)

    // Filter to executive — no executive reports exist
    await user.click(screen.getByRole('button', { name: /executive briefings/i }))

    expect(await screen.findByText(/Archive Isolated/i)).toBeInTheDocument()
  })
})

// ── Export buttons — ready report ─────────────────────────────────────────────

describe('Reports — export buttons on a ready report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('shows PDF, HTML and CSV buttons for a ready report', async () => {
    renderReports()

    expect(await screen.findByRole('button', { name: /^pdf$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^html$/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^csv$/i })).toBeInTheDocument()
  })

  it('export buttons are enabled for a ready report', async () => {
    renderReports()

    await screen.findByRole('button', { name: /^pdf$/i })

    expect(screen.getByRole('button', { name: /^pdf$/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).not.toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).not.toBeDisabled()
  })

  it('clicking PDF opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()

    await user.click(await screen.findByRole('button', { name: /^pdf$/i }))

    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/task/${readyReport.task_id}/report/pdf`),
      '_blank',
    )
  })

  it('clicking HTML opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()

    await user.click(await screen.findByRole('button', { name: /^html$/i }))

    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/task/${readyReport.task_id}/report/html`),
      '_blank',
    )
  })

  it('clicking CSV opens the correct backend URL', async () => {
    const user = userEvent.setup()
    renderReports()

    await user.click(await screen.findByRole('button', { name: /^csv$/i }))

    expect(openSpy).toHaveBeenCalledWith(
      expect.stringContaining(`/task/${readyReport.task_id}/report/csv`),
      '_blank',
    )
  })

  it('does not use the old placeholder latest-report route', async () => {
    const user = userEvent.setup()
    renderReports()

    await user.click(await screen.findByRole('button', { name: /^pdf$/i }))

    expect(openSpy).not.toHaveBeenCalledWith(
      expect.stringContaining('latest'),
      expect.anything(),
    )
  })
})

// ── Export buttons — non-ready reports ───────────────────────────────────────

describe('Reports — export buttons on a generating report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [generatingReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('export buttons are disabled when report is generating', async () => {
    renderReports()

    await screen.findByRole('button', { name: /^pdf$/i })

    expect(screen.getByRole('button', { name: /^pdf$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).toBeDisabled()
  })

  it('clicking a disabled button does not open any URL', async () => {
    const user = userEvent.setup()
    renderReports()

    await screen.findByRole('button', { name: /^pdf$/i })
    await user.click(screen.getByRole('button', { name: /^pdf$/i }))

    expect(openSpy).not.toHaveBeenCalled()
  })
})

describe('Reports — export buttons on a failed report', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [failedReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
    openSpy.mockClear()
  })

  it('export buttons are disabled when report has failed', async () => {
    renderReports()

    await screen.findByRole('button', { name: /^pdf$/i })

    expect(screen.getByRole('button', { name: /^pdf$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^html$/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /^csv$/i })).toBeDisabled()
  })
})

// ── Filter ────────────────────────────────────────────────────────────────────

describe('Reports — type filter', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({
      reports: [readyReport, generatingReport],
    })
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

    // Filter to executive — only generatingReport is executive
    await user.click(screen.getByRole('button', { name: /executive briefings/i }))

    await waitFor(() => {
      expect(screen.queryByText(/Security Scan — example.com/i)).not.toBeInTheDocument()
    })
    expect(screen.getByText(/Security Scan — staging.example.com/i)).toBeInTheDocument()
  })
})
