import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Findings from '../../../src/pages/Findings'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  getFindings: vi.fn(),
}))

vi.mock('../../../src/utils/exportUtils', () => ({
  exportFindingsAsCSV: vi.fn(),
  exportFindingsAsJSON: vi.fn(),
}))

import { exportFindingsAsCSV, exportFindingsAsJSON } from '../../../src/utils/exportUtils'

vi.mock('../../../src/utils/date', async (importOriginal: any) => {
  const actual = await importOriginal() as typeof import('../../../src/utils/date')
  return {
    ...actual,
    formatLocaleDate: (d: any) => (d ? '2024-01-01' : ''),
  }
})

const mockScrollToIndex = vi.fn()

vi.mock('@tanstack/react-virtual', async (importOriginal) => {
  const actual = await importOriginal<any>()
  return {
    ...actual,
    useVirtualizer: (options: any) => {
      const virtualizer = actual.useVirtualizer(options)
      return {
        ...virtualizer,
        scrollToIndex: mockScrollToIndex,
      }
    },
  }
})

// @tanstack/react-virtual needs ResizeObserver + scrollHeight in jsdom
if (typeof global.ResizeObserver === 'undefined') {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any
}

Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { configurable: true, value: 800 })
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })

import { getFindings } from '../../../src/api'

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeFinding(overrides: Partial<ReturnType<typeof baseFinding>> = {}) {
  return baseFinding(overrides)
}

function baseFinding(overrides: any = {}) {
  return {
    id: `f-${Math.random().toString(36).slice(2)}`,
    severity: 'high',
    category: 'Network',
    title: 'Test Finding',
    target: 'example.com',
    description: 'A test description',
    remediation: 'Fix it',
    discovered_at: '2024-01-01T00:00:00Z',
    cvss: 7.5,
    cve: undefined,
    ...overrides,
  }
}

function makeLargeDataset(count: number) {
  return Array.from({ length: count }, (_, i) =>
    makeFinding({
      id: `finding-${i}`,
      severity: ['critical', 'high', 'medium', 'low', 'info'][i % 5],
      title: `Finding ${i}`,
    }),
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Findings — virtualized list', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders the page header', async () => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    render(<Findings />)
    expect(screen.getByRole('heading', { name: /Findings/i })).toBeInTheDocument()
  })

  it('shows loading state then renders findings', async () => {
    const findings = [makeFinding({ title: 'SQL Injection' })]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())
    expect(screen.getAllByText('SQL Injection').length).toBeGreaterThan(0)
  })

  it('shows empty state when no findings match', async () => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    render(<Findings />)
    await waitFor(() => expect(screen.getByText(/No Findings Match/i)).toBeInTheDocument())
  })

  it('does not mount all rows to DOM with 500 findings (DOM bloat test)', async () => {
    const findings = makeLargeDataset(500)
    vi.mocked(getFindings).mockResolvedValue({ findings })

    const { container } = render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Only a small window of rows should be in the DOM — far fewer than 500
    const rows = container.querySelectorAll('[role="option"]')
    expect(rows.length).toBeLessThan(60)
  })

  it('filters findings by severity pill', async () => {
    const findings = [
      makeFinding({ id: 'c1', severity: 'critical', title: 'Critical Finding' }),
      makeFinding({ id: 'h1', severity: 'high', title: 'High Finding' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Click the Critical pill — use first match (the filter pill, not any row label)
    const criticalPill = screen.getAllByRole('button', { name: /Critical/i })[0]
    await userEvent.click(criticalPill)

    // Query within the virtual list only to avoid detail panel duplicates
    const list = screen.getByRole('listbox')
    expect(list.querySelector('[role="option"]')).toBeInTheDocument()
    expect(screen.getAllByText('Critical Finding').length).toBeGreaterThan(0)
    expect(screen.queryByText('High Finding')).not.toBeInTheDocument()
  })

  it('filters findings by search query', async () => {
    const findings = [
      makeFinding({ title: 'XSS Attack Vector', description: 'Cross site scripting' }),
      makeFinding({ title: 'SQL Injection', description: 'Database attack' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const searchInput = screen.getByPlaceholderText(/Title, target, CVE/i)
    await userEvent.type(searchInput, 'XSS')

    // Use getAllByText since title appears in both list row and detail panel
    expect(screen.getAllByText('XSS Attack Vector').length).toBeGreaterThan(0)
    expect(screen.queryByText('SQL Injection')).not.toBeInTheDocument()
  })

  it('selects a finding when clicked and shows it in the detail panel', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'Finding Alpha', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'Finding Beta', severity: 'critical' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Click within the list to select a different finding
    const listbox = screen.getByRole('listbox')
    const betaOption = listbox.querySelector('[role="option"][aria-label*="Finding Beta"], [role="option"]')
    if (betaOption) await userEvent.click(betaOption)

    expect(screen.getByText('Selected Finding')).toBeInTheDocument()
  })

  it('keyboard ArrowDown moves selection forward', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'First Finding', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'Second Finding', severity: 'critical' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const listbox = screen.getByRole('listbox')
    listbox.focus()
    fireEvent.keyDown(listbox, { key: 'ArrowDown' })

    await waitFor(() => {
      const selected = screen.getByRole('option', { name: /Second Finding/i })
      expect(selected).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('keyboard ArrowDown follows sorted order in non-severity sort mode', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'Alpha Finding', severity: 'high', discovered_at: '2024-01-01T00:00:00Z' }),
      makeFinding({ id: 'f2', title: 'Beta Finding', severity: 'critical', discovered_at: '2024-01-03T00:00:00Z' }),
      makeFinding({ id: 'f3', title: 'Gamma Finding', severity: 'medium', discovered_at: '2024-01-02T00:00:00Z' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Switch to "newest" sort — order should be f2 (Jan 3), f3 (Jan 2), f1 (Jan 1)
    const selects = screen.getAllByRole('combobox')
    const sortSelect = selects.find((s) =>
      Array.from(s.querySelectorAll('option')).some((o) => /Newest First/i.test(o.textContent || '')),
    )
    expect(sortSelect).toBeDefined()
    await userEvent.selectOptions(sortSelect!, 'newest')

    // Select the first item in the sorted list (Beta Finding), then ArrowDown should go to Gamma
    const betaOption = await screen.findByRole('option', { name: /Beta Finding/i })
    await userEvent.click(betaOption)

    const listbox = screen.getByRole('listbox')
    listbox.focus()
    fireEvent.keyDown(listbox, { key: 'ArrowDown' })

    await waitFor(() => {
      const selected = screen.getByRole('option', { name: /Gamma Finding/i })
      expect(selected).toHaveAttribute('aria-selected', 'true')
    })
  })

  it('workflow actions (mark reviewed, suppress, reopen) update status chip', async () => {
    const findings = [makeFinding({ id: 'f1', title: 'Actionable Finding', severity: 'high' })]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /Mark Reviewed/i }))

    await waitFor(() => {
      const reviewedChips = screen.getAllByText('reviewed')
      expect(reviewedChips.length).toBeGreaterThan(0)
    })
  })

  it('copies finding id and shows success feedback', async () => {
    const findings = [makeFinding({ id: 'f1', title: 'ID Copy Test' })]
    vi.mocked(getFindings).mockResolvedValue({ findings })
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const copyButton = screen.getByRole('button', { name: /Copy ID/i })
    await userEvent.click(copyButton)

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith('f1'))
    expect(copyButton).toHaveTextContent('Copied')
  })

  it('keeps copy state idle when finding id copy fails', async () => {
    const findings = [makeFinding({ id: 'f2', title: 'ID Copy Failure Test' })]
    vi.mocked(getFindings).mockResolvedValue({ findings })
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockRejectedValue(new Error('clipboard unavailable')) },
    })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const copyButton = screen.getByRole('button', { name: /Copy ID/i })
    await userEvent.click(copyButton)

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith('f2'))
    expect(copyButton).toHaveTextContent('Copy ID')
  })

  it('persists review state to localStorage', async () => {
    const findings = [makeFinding({ id: 'f1', title: 'Persist Test', severity: 'high' })]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /Mark Reviewed/i }))

    const stored = JSON.parse(localStorage.getItem('secuscan-finding-review-state') ?? '{}')
    expect(stored['f1']).toBe('reviewed')
  })

  it('negative: suppressed finding shows suppressed status chip', async () => {
    const findings = [
      makeFinding({ id: 's1', title: 'Suppressed Finding', severity: 'low' }),
      makeFinding({ id: 'a1', title: 'Active Finding', severity: 'high' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    localStorage.setItem('secuscan-finding-review-state', JSON.stringify({ s1: 'suppressed' }))

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const suppressedChips = screen.queryAllByText('suppressed')
    expect(suppressedChips.length).toBeGreaterThan(0)
  })

  it('renders filter section with correct layout classes to prevent overlap', async () => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const targetLabel = screen.getByText('Target')
    const fieldContainer = targetLabel.closest('div')
    expect(fieldContainer).toHaveClass('space-y-2', 'min-w-0')

    const gridContainer = fieldContainer?.parentElement
    expect(gridContainer).toHaveClass('grid', 'gap-4', 'sm:grid-cols-2', 'lg:grid-cols-3', 'xl:grid-cols-4')

    const filterContainer = gridContainer?.parentElement
    expect(filterContainer).toHaveClass('flex', 'flex-col', 'gap-6')
  })

  it('individual checkbox click selects finding for export but doesn\'t change selected finding details', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'SQL Injection', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'CSRF Vulnerability', severity: 'high' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const checkboxF2 = screen.getByLabelText('Select CSRF Vulnerability')
    expect(checkboxF2).not.toBeChecked()

    await userEvent.click(checkboxF2)
    expect(checkboxF2).toBeChecked()

    expect(screen.getByRole('button', { name: /Bulk Export/i })).toBeInTheDocument()

    expect(screen.getByRole('heading', { name: /SQL Injection/i, level: 2 })).toBeInTheDocument()
  })

  it('select all checkbox toggles selection for all visible findings', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'SQL Injection', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'CSRF Vulnerability', severity: 'high' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    const selectAllCheckbox = screen.getByLabelText(/Select All Visible/i)
    await userEvent.click(selectAllCheckbox)

    expect(screen.getByLabelText('Select SQL Injection')).toBeChecked()
    expect(screen.getByLabelText('Select CSRF Vulnerability')).toBeChecked()

    await userEvent.click(selectAllCheckbox)
    expect(screen.getByLabelText('Select SQL Injection')).not.toBeChecked()
    expect(screen.getByLabelText('Select CSRF Vulnerability')).not.toBeChecked()
  })

  it('trigger CSV and JSON bulk export calls utility function', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'SQL Injection', severity: 'critical' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    await userEvent.click(screen.getByLabelText('Select SQL Injection'))

    const bulkExportBtn = screen.getByRole('button', { name: /Bulk Export/i })
    await userEvent.click(bulkExportBtn)

    const csvExportBtn = screen.getByRole('button', { name: /Export as CSV/i })
    const jsonExportBtn = screen.getByRole('button', { name: /Export as JSON/i })

    expect(csvExportBtn).toBeInTheDocument()
    expect(jsonExportBtn).toBeInTheDocument()

    await userEvent.click(csvExportBtn)
    expect(exportFindingsAsCSV).toHaveBeenCalled()

    await userEvent.click(bulkExportBtn)
    const newJsonExportBtn = await screen.findByRole('button', { name: /Export as JSON/i })
    await userEvent.click(newJsonExportBtn)
    expect(exportFindingsAsJSON).toHaveBeenCalled()
  })
})

describe('Findings — severity legend help affordance', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  async function renderReady() {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    render(<Findings />)
    await waitFor(() =>
      expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument(),
    )
  }

  const triggerName = /what do the severity levels mean/i
  const dialogName = /severity scale legend/i

  it('legend is collapsed by default', async () => {
    await renderReady()
    expect(screen.getByRole('button', { name: triggerName })).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('dialog', { name: dialogName })).not.toBeInTheDocument()
  })

  it('opens the legend and lists every severity with a description and ordering note', async () => {
    await renderReady()
    const trigger = screen.getByRole('button', { name: triggerName })
    await userEvent.click(trigger)

    const dialog = screen.getByRole('dialog', { name: dialogName })
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(within(dialog).getByText(/ordered highest/i)).toBeInTheDocument()
    for (const label of ['Critical', 'High', 'Medium', 'Low', 'Info']) {
      expect(within(dialog).getByText(label)).toBeInTheDocument()
    }
    // A representative plain-language blurb is present
    expect(within(dialog).getByText(/triage first/i)).toBeInTheDocument()
  })

  it('closes the legend on Escape and restores focus to the trigger', async () => {
    await renderReady()
    const trigger = screen.getByRole('button', { name: triggerName })
    await userEvent.click(trigger)
    expect(screen.getByRole('dialog', { name: dialogName })).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: dialogName })).not.toBeInTheDocument(),
    )
    expect(trigger).toHaveFocus()
  })

  it('closes the legend via the close button', async () => {
    await renderReady()
    await userEvent.click(screen.getByRole('button', { name: triggerName }))
    await userEvent.click(screen.getByRole('button', { name: /close severity legend/i }))
    await waitFor(() =>
      expect(screen.queryByRole('dialog', { name: dialogName })).not.toBeInTheDocument(),
    )
  })
})

describe('Findings — virtualizer scrolling', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('changing the selected finding triggers the expected scroll call', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'Finding Alpha', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'Finding Beta', severity: 'high' }),
      makeFinding({ id: 'f3', title: 'Finding Gamma', severity: 'medium' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Clear initial scroll call on mount
    mockScrollToIndex.mockClear()

    // Click Finding Beta to select it
    const betaOption = await screen.findByRole('option', { name: /Finding Beta/i })
    await userEvent.click(betaOption)

    // Assert it called scrollToIndex with correct index (1)
    expect(mockScrollToIndex).toHaveBeenCalledWith(1, { align: 'auto', behavior: 'smooth' })
  })

  it('filtering/sorting does not scroll to stale indexes', async () => {
    const findings = [
      makeFinding({ id: 'f1', title: 'Finding Alpha', severity: 'critical' }),
      makeFinding({ id: 'f2', title: 'Finding Beta', severity: 'high' }),
      makeFinding({ id: 'f3', title: 'Finding Gamma', severity: 'medium' }),
    ]
    vi.mocked(getFindings).mockResolvedValue({ findings })

    render(<Findings />)
    await waitFor(() => expect(screen.queryByText('Synchronizing findings feed...')).not.toBeInTheDocument())

    // Select Beta (triggers scroll) and then clear mocks
    const betaOption = await screen.findByRole('option', { name: /Finding Beta/i })
    await userEvent.click(betaOption)
    expect(mockScrollToIndex).toHaveBeenCalled()
    mockScrollToIndex.mockClear()

    // Filter using search query that includes Beta
    const searchInput = screen.getByPlaceholderText(/Title, target, CVE/i)
    await userEvent.type(searchInput, 'Beta')

    // Expect no scrollToIndex call because selectedFindingId did not change
    expect(mockScrollToIndex).not.toHaveBeenCalled()

    // Clear search query
    await userEvent.clear(searchInput)
    expect(mockScrollToIndex).not.toHaveBeenCalled()

    // Change sorting mode (while Beta remains visible/selected)
    const selects = screen.getAllByRole('combobox')
    const sortSelect = selects.find((s) =>
      Array.from(s.querySelectorAll('option')).some((o) => /Newest First/i.test(o.textContent || '')),
    )
    expect(sortSelect).toBeDefined()
    await userEvent.selectOptions(sortSelect!, 'newest')

    // Expect no scrollToIndex call
    expect(mockScrollToIndex).not.toHaveBeenCalled()
  })
})
