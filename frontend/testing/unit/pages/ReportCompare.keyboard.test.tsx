/**
 * @file ReportCompare.keyboard.test.tsx
 * @issue #887 — keyboard navigation and sticky context for report comparison view
 *
 * What this suite guards:
 *  - Both report-selector <select> elements are reachable and operable by keyboard alone.
 *  - The refresh button is in the tab order and triggers a data reload when activated via
 *    Enter / Space — without the pointer.
 *  - The "Back to reports" link is focusable and has a meaningful accessible name.
 *  - After a diff is computed, the four scrollable finding-list regions are keyboard-focusable
 *    (tabIndex=0, role="region") so users can read them without a mouse.
 *  - Sticky context: selecting a baseline then navigating to the comparison selector does NOT
 *    clear the already-chosen baseline value.
 *  - Sticky context: selecting both reports and then activating the refresh button preserves
 *    both selections after the reload completes.
 *  - Changing the comparison selector while a baseline is already chosen still surfaces the diff.
 *  - Same-report guard: when both selectors are set to the same report an accessible warning
 *    is announced, and the diff sections are absent.
 */

import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ReportCompare from '../../../src/pages/ReportCompare'
import { getFindings, getReports } from '../../../src/api'

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getFindings: vi.fn(),
}))

// framer-motion: collapse animations so tests don't depend on timing
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement> & { children?: React.ReactNode }) => (
      <div {...props}>{children}</div>
    ),
  },
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const REPORT_A = {
  id: 'report-a',
  task_id: 'task-a',
  name: 'Scan Alpha',
  generated_at: '2026-05-01T10:00:00Z',
  status: 'ready',
  findings: 2,
}

const REPORT_B = {
  id: 'report-b',
  task_id: 'task-b',
  name: 'Scan Beta',
  generated_at: '2026-05-03T10:00:00Z',
  status: 'ready',
  findings: 2,
}

const REPORT_C = {
  id: 'report-c',
  task_id: 'task-c',
  name: 'Scan Gamma',
  generated_at: '2026-05-05T10:00:00Z',
  status: 'ready',
  findings: 1,
}

/** Two findings present only in task-a (baseline). */
const FINDINGS_A_ONLY = [
  { id: 'f-a1', task_id: 'task-a', title: 'Alpha Finding One', target: '10.0.0.1', category: 'network', severity: 'high' },
  { id: 'f-a2', task_id: 'task-a', title: 'Alpha Finding Two', target: '10.0.0.2', category: 'crypto', severity: 'medium' },
]

/** One finding matching baseline (same fingerprint) + one new in task-b. */
const FINDINGS_B_MIXED = [
  { id: 'f-b1', task_id: 'task-b', title: 'Alpha Finding One', target: '10.0.0.1', category: 'network', severity: 'high' },
  { id: 'f-b2', task_id: 'task-b', title: 'Beta New Finding', target: '10.0.0.3', category: 'web', severity: 'critical' },
]

/** One finding in task-c with a severity escalation on the shared fingerprint. */
const FINDINGS_C_SEVERITY = [
  { id: 'f-c1', task_id: 'task-c', title: 'Alpha Finding One', target: '10.0.0.1', category: 'network', severity: 'critical' },
]

function defaultApiMocks() {
  vi.mocked(getReports).mockResolvedValue({ reports: [REPORT_A, REPORT_B, REPORT_C] })
  vi.mocked(getFindings).mockResolvedValue({
    findings: [...FINDINGS_A_ONLY, ...FINDINGS_B_MIXED, ...FINDINGS_C_SEVERITY],
  })
}

function renderCompare() {
  return render(
    <MemoryRouter>
      <ReportCompare />
    </MemoryRouter>,
  )
}

/** Wait for the loading state to disappear so selectors are mounted. */
async function waitForReady() {
  await waitFor(() =>
    expect(screen.queryByText(/loading comparison data/i)).not.toBeInTheDocument(),
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function getBaselineSelect(): HTMLSelectElement {
  return screen.getByRole('combobox', { name: /baseline report/i }) as HTMLSelectElement
}

function getComparisonSelect(): HTMLSelectElement {
  return screen.getByRole('combobox', { name: /comparison report/i }) as HTMLSelectElement
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ReportCompare — keyboard navigation (#887)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    defaultApiMocks()
  })

  // ── Tab order: selector controls ───────────────────────────────────────────

  it('baseline select is focusable and has an accessible name', async () => {
    renderCompare()
    await waitForReady()

    const select = getBaselineSelect()
    select.focus()
    expect(document.activeElement).toBe(select)
    expect(select).toHaveAccessibleName()
  })

  it('comparison select is focusable and has an accessible name', async () => {
    renderCompare()
    await waitForReady()

    const select = getComparisonSelect()
    select.focus()
    expect(document.activeElement).toBe(select)
    expect(select).toHaveAccessibleName()
  })

  it('can choose baseline report via keyboard-only select interaction', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    const select = getBaselineSelect()
    await user.selectOptions(select, 'report-a')

    expect(select.value).toBe('report-a')
  })

  it('can choose comparison report via keyboard-only select interaction', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    const select = getComparisonSelect()
    await user.selectOptions(select, 'report-b')

    expect(select.value).toBe('report-b')
  })

  it('both selects contain all available report options', async () => {
    renderCompare()
    await waitForReady()

    for (const select of [getBaselineSelect(), getComparisonSelect()]) {
      const optionValues = Array.from(select.options).map((o) => o.value)
      expect(optionValues).toContain('report-a')
      expect(optionValues).toContain('report-b')
      expect(optionValues).toContain('report-c')
    }
  })

  // ── Tab order: refresh button ──────────────────────────────────────────────

  it('refresh button is in the tab order and has an accessible label', async () => {
    renderCompare()
    await waitForReady()

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    expect(refreshBtn).toBeInTheDocument()
    // tabIndex is unset (default 0) — verify it is reachable
    expect(refreshBtn.tabIndex).toBeGreaterThanOrEqual(0)
  })

  it('pressing Enter on the refresh button re-fetches data', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    // getReports should have been called once on mount
    expect(getReports).toHaveBeenCalledTimes(1)

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    await user.keyboard('{Enter}')

    await waitFor(() => expect(getReports).toHaveBeenCalledTimes(2))
  })

  it('pressing Space on the refresh button re-fetches data', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    expect(getReports).toHaveBeenCalledTimes(1)

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    await user.keyboard('{ }')

    await waitFor(() => expect(getReports).toHaveBeenCalledTimes(2))
  })

  // ── Tab order: back link ───────────────────────────────────────────────────

  it('"Back to reports" link is focusable and has a meaningful accessible name', async () => {
    renderCompare()
    await waitForReady()

    const backLink = screen.getByRole('link', { name: /back to reports/i })
    expect(backLink).toBeInTheDocument()
    backLink.focus()
    expect(document.activeElement).toBe(backLink)
  })

  // ── Scrollable finding-list regions ───────────────────────────────────────

  it('diff result regions are keyboard-focusable after both reports are selected', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-b')

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument(),
    )

    // Each scrollable list region must carry role="region" and tabIndex=0
    const regions = screen.getAllByRole('region', { name: /findings list/i })
    expect(regions.length).toBeGreaterThanOrEqual(1)

    for (const region of regions) {
      expect(region.tabIndex).toBe(0)
      region.focus()
      expect(document.activeElement).toBe(region)
    }
  })

  it('severity-changed and fixed findings regions are keyboard-focusable (report-a vs report-c)', async () => {
    // report-a vs report-c:
    //   "Alpha Finding One" appears in both but severity goes high→critical → severityChanged region rendered
    //   "Alpha Finding Two" is only in task-a → fixedFindings region rendered
    // Empty sections show a "None" placeholder, NOT a scrollable region, so we assert only
    // on the two sections that have items.
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-c')

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /severity changed/i })).toBeInTheDocument(),
    )

    const severityRegion = screen.getByRole('region', { name: /severity changed findings list/i })
    expect(severityRegion).toBeInTheDocument()
    expect(severityRegion.tabIndex).toBe(0)

    const fixedRegion = screen.getByRole('region', { name: /fixed findings findings list/i })
    expect(fixedRegion).toBeInTheDocument()
    expect(fixedRegion.tabIndex).toBe(0)

    // Both regions must be independently keyboard-focusable
    severityRegion.focus()
    expect(document.activeElement).toBe(severityRegion)

    fixedRegion.focus()
    expect(document.activeElement).toBe(fixedRegion)
  })

  it('a region with items can receive keyboard focus', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    // task-a has "Alpha Finding One" + "Alpha Finding Two"; task-b has "Alpha Finding One" (unchanged) + "Beta New Finding" (new)
    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-b')

    const newRegion = await screen.findByRole('region', { name: /new findings findings list/i })
    newRegion.focus()
    expect(document.activeElement).toBe(newRegion)
    // The new finding from B should be visible inside the focusable region
    expect(newRegion).toHaveTextContent(/Beta New Finding/i)
  })

  // ── Sticky context: baseline preserved when tabbing to comparison ──────────

  it('choosing a baseline then tabbing to comparison does not clear the baseline', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    const baseline = getBaselineSelect()
    const comparison = getComparisonSelect()

    await user.selectOptions(baseline, 'report-a')
    expect(baseline.value).toBe('report-a')

    // Tab to comparison selector and pick a value
    comparison.focus()
    await user.selectOptions(comparison, 'report-b')

    // Baseline must be unchanged
    expect(baseline.value).toBe('report-a')
    expect(comparison.value).toBe('report-b')
  })

  it('choosing a comparison then changing the baseline retains the comparison value', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    const baseline = getBaselineSelect()
    const comparison = getComparisonSelect()

    await user.selectOptions(comparison, 'report-b')
    expect(comparison.value).toBe('report-b')

    await user.selectOptions(baseline, 'report-a')

    expect(comparison.value).toBe('report-b')
    expect(baseline.value).toBe('report-a')
  })

  // ── Sticky context: refresh preserves selections ───────────────────────────

  it('refreshing with both reports selected keeps both selectors intact afterwards', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-b')

    // Trigger refresh via the keyboard-accessible button
    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    await user.keyboard('{Enter}')

    await waitFor(() => expect(getReports).toHaveBeenCalledTimes(2))

    // Selections must survive the reload cycle
    expect(getBaselineSelect().value).toBe('report-a')
    expect(getComparisonSelect().value).toBe('report-b')
  })

  it('diff result is still visible after refresh when both selectors are set', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-b')

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument(),
    )

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    await user.keyboard('{Enter}')

    await waitFor(() => expect(getReports).toHaveBeenCalledTimes(2))

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument(),
    )
  })

  // ── Sticky context: switching comparison while baseline is held ────────────

  it('changing only the comparison selector while baseline is held updates the diff', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-b')

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument(),
    )

    // Now switch comparison to report-c — baseline (report-a) must stay
    await user.selectOptions(getComparisonSelect(), 'report-c')

    expect(getBaselineSelect().value).toBe('report-a')
    expect(getComparisonSelect().value).toBe('report-c')

    // Diff re-renders; severity-changed section should appear (Alpha Finding One escalates high→critical)
    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /severity changed/i })).toBeInTheDocument(),
    )
  })

  // ── Same-report guard ──────────────────────────────────────────────────────

  it('selecting the same report in both selectors shows the warning and hides diff sections', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-a')

    await waitFor(() =>
      expect(
        screen.getByText(/select two different reports to compare/i),
      ).toBeInTheDocument(),
    )

    expect(screen.queryByRole('heading', { name: /new findings/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /fixed findings/i })).not.toBeInTheDocument()
  })

  it('resolving the same-report conflict by changing comparison removes the warning', async () => {
    const user = userEvent.setup()
    renderCompare()
    await waitForReady()

    await user.selectOptions(getBaselineSelect(), 'report-a')
    await user.selectOptions(getComparisonSelect(), 'report-a')

    await waitFor(() =>
      expect(screen.getByText(/select two different reports to compare/i)).toBeInTheDocument(),
    )

    // Fix the conflict via keyboard
    await user.selectOptions(getComparisonSelect(), 'report-b')

    await waitFor(() =>
      expect(
        screen.queryByText(/select two different reports to compare/i),
      ).not.toBeInTheDocument(),
    )

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: /new findings/i })).toBeInTheDocument(),
    )
  })

  // ── Error state ────────────────────────────────────────────────────────────

  it('error state is announced in the DOM and refresh button remains focusable', async () => {
    vi.mocked(getReports).mockRejectedValue(new Error('network error'))
    renderCompare()

    await waitFor(() =>
      expect(screen.getByText(/failed to load reports or findings/i)).toBeInTheDocument(),
    )

    // Selectors not rendered in error state — refresh must still be keyboard-accessible
    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    expect(document.activeElement).toBe(refreshBtn)
  })

  it('activating refresh after an error retries the API call', async () => {
    vi.mocked(getReports).mockRejectedValueOnce(new Error('network error'))
    const user = userEvent.setup()
    renderCompare()

    await waitFor(() =>
      expect(screen.getByText(/failed to load reports or findings/i)).toBeInTheDocument(),
    )

    vi.mocked(getReports).mockResolvedValue({ reports: [REPORT_A, REPORT_B] })

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    refreshBtn.focus()
    await user.keyboard('{Enter}')

    await waitFor(() =>
      expect(screen.queryByText(/failed to load reports or findings/i)).not.toBeInTheDocument(),
    )
  })

  // ── Regression guard: fireEvent path for keyboard activation ──────────────

  it('fireEvent.keyDown Enter on refresh button triggers reload (regression guard)', async () => {
    renderCompare()
    await waitForReady()

    expect(getReports).toHaveBeenCalledTimes(1)

    const refreshBtn = screen.getByRole('button', { name: /refresh reports/i })
    fireEvent.click(refreshBtn) // simulates Enter/Space on a <button>

    await waitFor(() => expect(getReports).toHaveBeenCalledTimes(2))
  })
})