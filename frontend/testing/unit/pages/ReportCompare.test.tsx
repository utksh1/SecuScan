import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ReportCompare from '../../../src/pages/ReportCompare'
import { getFindings, getReports } from '../../../src/api'

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getFindings: vi.fn(),
}))

const readyA = {
  id: 'report-a',
  task_id: 'task-a',
  name: 'Scan A',
  type: 'technical',
  generated_at: '2026-05-01T10:00:00Z',
  status: 'ready',
  findings: 1,
  assets: 1,
  pages: 1,
}

const readyB = {
  id: 'report-b',
  task_id: 'task-b',
  name: 'Scan B',
  type: 'technical',
  generated_at: '2026-05-02T10:00:00Z',
  status: 'ready',
  findings: 2,
  assets: 1,
  pages: 1,
}

function renderCompare() {
  return render(
    <MemoryRouter>
      <ReportCompare />
    </MemoryRouter>,
  )
}

describe('ReportCompare page', () => {
  beforeEach(() => {
    vi.mocked(getReports).mockResolvedValue({ reports: [readyA, readyB] })
    vi.mocked(getFindings).mockResolvedValue({
      findings: [
        {
          id: 'f1',
          task_id: 'task-a',
          title: 'Only in A',
          target: '127.0.0.1',
          category: 'network',
          severity: 'high',
        },
        {
          id: 'f2',
          task_id: 'task-b',
          title: 'Only in A',
          target: '127.0.0.1',
          category: 'network',
          severity: 'high',
        },
        {
          id: 'f3',
          task_id: 'task-b',
          title: 'Only in B',
          target: '127.0.0.1',
          category: 'network',
          severity: 'critical',
        },
      ],
    })
  })

  it('lists failed reports when they still have findings', async () => {
    vi.mocked(getReports).mockResolvedValue({
      reports: [
        { ...readyA, status: 'failed' },
        { ...readyB, status: 'failed' },
      ],
    })
    renderCompare()

    await waitFor(() => {
      const options = screen.getAllByRole('option')
      expect(options.some((o) => o.textContent?.includes('Scan A'))).toBe(true)
      expect(options.some((o) => o.textContent?.includes('Scan B'))).toBe(true)
    })
  })

  it('renders compare selectors and diff sections', async () => {
    const user = userEvent.setup()
    renderCompare()

    expect(await screen.findByRole('heading', { name: /compare reports/i })).toBeInTheDocument()

    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'report-a')
    await user.selectOptions(selects[1], 'report-b')

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /fixed findings/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /^unchanged$/i })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: /severity changed/i })).toBeInTheDocument()
      expect(screen.getByText(/Only in B/i)).toBeInTheDocument()
    })
  })

  it('allows keyboard navigation', async () => {
    const user = userEvent.setup()
    renderCompare()

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /compare reports/i })).toBeInTheDocument()
    })

    const selects = screen.getAllByRole('combobox')
    await user.tab()
    expect(selects[0]).toHaveFocus()

    await user.tab()
    expect(selects[1]).toHaveFocus()

    await user.selectOptions(selects[0], 'report-a')
    await user.selectOptions(selects[1], 'report-b')

    await waitFor(() => {
      expect(screen.getByText(/Only in B/i)).toBeInTheDocument()
    })

    await user.tab()
    const refreshButton = screen.getByTitle('Refresh')
    expect(refreshButton).toHaveFocus()
  })

  it('keeps context while scrolling within a findings list (sticky header regression guard)', async () => {
    const user = userEvent.setup()
    renderCompare()

    const selects = await screen.findAllByRole('combobox')
    await user.selectOptions(selects[0], 'report-a')
    await user.selectOptions(selects[1], 'report-b')

    // Ensure the compare sections are rendered.
    const sectionHeader = await screen.findByRole('heading', { name: /new findings/i })
    expect(sectionHeader).toBeInTheDocument()

    // The findings list is the scroll container inside that section.
    const scrollContainer = sectionHeader
      .closest('section')
      ?.querySelector('div.max-h-80.overflow-y-auto') as HTMLElement | null

    // JSDOM doesn't do real layout, but the regression guard is about keyboard focus/context,
    // not about pixel-perfect sticky rendering.
    expect(scrollContainer).not.toBeNull()

    // Use the refresh button (focusable) to validate context retention.
    // Scroll shouldn’t cause re-render/focus loss.
    await user.tab() // from combobox[0]
    await user.tab() // from combobox[1]
    const refreshButton = screen.getByTitle('Refresh')
    expect(refreshButton).toHaveFocus()

    scrollContainer!.scrollTop = 50
    scrollContainer!.dispatchEvent(new Event('scroll'))

    expect(screen.getByRole('heading', { name: /new findings/i })).toBe(sectionHeader)
    expect(document.activeElement).toBe(refreshButton)
  })
})
