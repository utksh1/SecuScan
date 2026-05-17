import { render, screen, waitFor, within, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Findings from '../../../src/pages/Findings'
import { getFindings } from '../../../src/api'
import * as dateUtils from '../../../src/utils/date'

vi.mock('../../../src/api', () => ({
  getFindings: vi.fn(),
  API_BASE: 'http://127.0.0.1:8000',
}))

// ── Fixtures ──────────────────────────────────────────────────────────────────

const criticalFinding = {
  id: 'finding-crit-1',
  severity: 'critical',
  category: 'injection',
  title: 'SQL Injection in Login',
  target: 'api.example.com',
  description: 'Parameterized queries not used.',
  remediation: 'Use prepared statements.',
  discovered_at: '2026-05-14T10:00:00Z',
  cvss: 9.8,
  cve: 'CVE-2026-1234',
  plugin_id: 'sqlmap',
}

const highFinding = {
  id: 'finding-high-1',
  severity: 'high',
  category: 'xss',
  title: 'Stored XSS in Comments',
  target: 'web.example.com',
  description: 'User input rendered without escaping.',
  remediation: 'Sanitize output.',
  discovered_at: '2026-05-13T08:30:00Z',
  cvss: 7.5,
  plugin_id: 'zap',
}

const mediumFinding = {
  id: 'finding-med-1',
  severity: 'medium',
  category: 'misconfiguration',
  title: 'Missing Security Headers',
  target: 'api.example.com',
  description: 'Several headers are absent.',
  remediation: 'Add CSP and HSTS headers.',
  discovered_at: '2026-05-15T14:00:00Z',
  plugin_id: 'nikto',
}

const allFindings = [criticalFinding, highFinding, mediumFinding]

// ── Helpers ───────────────────────────────────────────────────────────────────

function renderFindings() {
  return render(
    <MemoryRouter>
      <Findings />
    </MemoryRouter>,
  )
}

/** Wait for data to load by looking for a known finding title. */
async function waitForLoad() {
  await waitFor(() => {
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
  })
}

/** Helper to grab the sort select via its label. */
function getSortSelect() {
  const label = screen.getByText('Sort By')
  return label.parentElement!.querySelector('select')!
}

/** Helper to collect visible finding titles from the list section. */
function getVisibleTitles() {
  // h3 tags in the list hold finding titles
  return Array.from(document.querySelectorAll('h3'))
    .map((el) => el.textContent ?? '')
    .filter(Boolean)
}

// ── Loading ───────────────────────────────────────────────────────────────────

describe('Findings — loading state', () => {
  it('shows loading text while fetching', () => {
    vi.mocked(getFindings).mockReturnValue(new Promise(() => {}))
    renderFindings()
    expect(screen.getByText(/Synchronizing findings feed/i)).toBeInTheDocument()
  })
})

// ── Severity filter ───────────────────────────────────────────────────────────

describe('Findings — severity filtering', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('shows all findings by default', async () => {
    renderFindings()
    await waitForLoad()
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Missing Security Headers').length).toBeGreaterThanOrEqual(1)
  })

  it('filters to critical only when critical pill is clicked', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const critButtons = screen.getAllByRole('button', { name: /critical/i })
    const toggle = critButtons.find((btn) => btn.textContent?.includes('1'))
    expect(toggle).toBeTruthy()
    await user.click(toggle!)

    await waitFor(() => {
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
  })
})

// ── Sort options ──────────────────────────────────────────────────────────────

describe('Findings — sorting', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('sort dropdown contains all expected options', async () => {
    renderFindings()
    await waitForLoad()

    const options = within(getSortSelect()).getAllByRole('option')
    const labels = options.map((o) => o.textContent)
    expect(labels).toContain('Newest First')
    expect(labels).toContain('Oldest First')
    expect(labels).toContain('Target (A → Z)')
  })

  it('switches to flat list when sort is newest', async () => {
    renderFindings()
    await waitForLoad()

    fireEvent.change(getSortSelect(), { target: { value: 'newest' } })

    await waitFor(() => {
      const headers = screen.getAllByText(/visible in queue/i)
      expect(headers.length).toBe(1)
    })
  })

  it('newest-first puts most recent finding on top', async () => {
    renderFindings()
    await waitForLoad()

    fireEvent.change(getSortSelect(), { target: { value: 'newest' } })

    await waitFor(() => {
      const titles = getVisibleTitles()
      // May 15 > May 14 > May 13
      expect(titles.indexOf('Missing Security Headers')).toBeLessThan(titles.indexOf('SQL Injection in Login'))
      expect(titles.indexOf('SQL Injection in Login')).toBeLessThan(titles.indexOf('Stored XSS in Comments'))
    })
  })

  it('oldest-first puts earliest finding on top', async () => {
    renderFindings()
    await waitForLoad()

    fireEvent.change(getSortSelect(), { target: { value: 'oldest' } })

    await waitFor(() => {
      const titles = getVisibleTitles()
      // May 13 < May 14 < May 15
      expect(titles.indexOf('Stored XSS in Comments')).toBeLessThan(titles.indexOf('SQL Injection in Login'))
      expect(titles.indexOf('SQL Injection in Login')).toBeLessThan(titles.indexOf('Missing Security Headers'))
    })
  })

  it('target A-Z sorts alphabetically by target', async () => {
    renderFindings()
    await waitForLoad()

    fireEvent.change(getSortSelect(), { target: { value: 'target' } })

    await waitFor(() => {
      const titles = getVisibleTitles()
      // api.example.com comes before web.example.com
      // criticalFinding and mediumFinding share api.example.com, highFinding has web.example.com
      const webIdx = titles.indexOf('Stored XSS in Comments')
      const apiIdx = titles.indexOf('SQL Injection in Login')
      expect(apiIdx).toBeLessThan(webIdx)
    })
  })
})

// ── Target filter ─────────────────────────────────────────────────────────────

describe('Findings — target filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('renders unique targets in dropdown', async () => {
    renderFindings()
    await waitForLoad()

    const targetSelect = screen.getByDisplayValue(/All Targets/i)
    const options = within(targetSelect as HTMLElement).getAllByRole('option')
    const labels = options.map((o) => o.textContent)

    expect(labels).toContain('All Targets')
    expect(labels).toContain('api.example.com')
    expect(labels).toContain('web.example.com')
  })

  it('filters findings when a specific target is selected', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const targetSelect = screen.getByDisplayValue(/All Targets/i)
    await user.selectOptions(targetSelect, 'web.example.com')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
  })
})

// ── Scanner / tool filter ─────────────────────────────────────────────────────

describe('Findings — scanner filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('renders unique scanners in dropdown', async () => {
    renderFindings()
    await waitForLoad()

    const scannerSelect = screen.getByDisplayValue(/All Scanners/i)
    const options = within(scannerSelect as HTMLElement).getAllByRole('option')
    const labels = options.map((o) => o.textContent)

    expect(labels).toContain('All Scanners')
    expect(labels).toContain('sqlmap')
    expect(labels).toContain('zap')
    expect(labels).toContain('nikto')
  })

  it('filters findings to one scanner', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const scannerSelect = screen.getByDisplayValue(/All Scanners/i)
    await user.selectOptions(scannerSelect, 'zap')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
      expect(screen.queryByText('Missing Security Headers')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
  })
})

// ── Date range filter ─────────────────────────────────────────────────────────

describe('Findings — date range filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('filters out findings before the from-date', async () => {
    renderFindings()
    await waitForLoad()

    // Set from-date to May 14 — should exclude the May 13 finding (highFinding)
    const fromLabel = screen.getByText('From Date')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    fireEvent.change(fromInput, { target: { value: '2026-05-14' } })

    await waitFor(() => {
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Missing Security Headers').length).toBeGreaterThanOrEqual(1)
  })

  it('filters out findings after the to-date', async () => {
    renderFindings()
    await waitForLoad()

    // Set to-date to May 14 — should exclude the May 15 finding (mediumFinding)
    const toLabel = screen.getByText('To Date')
    const toInput = toLabel.parentElement!.querySelector('input')!
    fireEvent.change(toInput, { target: { value: '2026-05-14' } })

    await waitFor(() => {
      expect(screen.queryByText('Missing Security Headers')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
  })

  it('includes findings on the boundary date', async () => {
    renderFindings()
    await waitForLoad()

    // Set from=May 14, to=May 14 — should include criticalFinding (discovered May 14)
    const fromLabel = screen.getByText('From Date')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    const toLabel = screen.getByText('To Date')
    const toInput = toLabel.parentElement!.querySelector('input')!

    fireEvent.change(fromInput, { target: { value: '2026-05-14' } })
    fireEvent.change(toInput, { target: { value: '2026-05-14' } })

    await waitFor(() => {
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
      expect(screen.queryByText('Missing Security Headers')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
  })
})

// ── Reset button ──────────────────────────────────────────────────────────────

describe('Findings — reset filters', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('clears all active filters when reset is clicked', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    // Apply a target filter first
    const targetSelect = screen.getByDisplayValue(/All Targets/i)
    await user.selectOptions(targetSelect, 'web.example.com')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
    })

    // Now click reset
    await user.click(screen.getByRole('button', { name: /reset filters/i }))

    await waitFor(() => {
      expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
    })
  })
})

// ── Timezone boundary regression ──────────────────────────────────────────────
// A finding at 2026-05-13T20:00:00Z is May 14 01:30 in Asia/Kolkata (IST).
// The date filter should compare by the *displayed* calendar day, not UTC.

describe('Findings — date range respects display timezone', () => {
  const tzBoundaryFinding = {
    id: 'finding-tz-edge',
    severity: 'high',
    category: 'xss',
    title: 'TZ Boundary XSS',
    target: 'tz.example.com',
    description: 'Edge case across UTC day boundary.',
    remediation: 'Fix it.',
    discovered_at: '2026-05-13T20:00:00Z',  // May 13 UTC, but May 14 in IST
    plugin_id: 'zap',
  }

  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [tzBoundaryFinding] })
    // Force timezone to Asia/Kolkata so the finding displays as May 14
    vi.spyOn(dateUtils, 'getCurrentTimeZone').mockReturnValue('Asia/Kolkata')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('includes a UTC May-13 finding when from-date is May-14 in IST', async () => {
    renderFindings()

    await waitFor(() => {
      expect(screen.getAllByText('TZ Boundary XSS').length).toBeGreaterThanOrEqual(1)
    })

    const fromLabel = screen.getByText('From Date')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    fireEvent.change(fromInput, { target: { value: '2026-05-14' } })

    // In IST this finding is May 14, so from-date of May 14 should keep it
    await waitFor(() => {
      expect(screen.getAllByText('TZ Boundary XSS').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('excludes the finding when from-date is May-15 in IST', async () => {
    renderFindings()

    await waitFor(() => {
      expect(screen.getAllByText('TZ Boundary XSS').length).toBeGreaterThanOrEqual(1)
    })

    const fromLabel = screen.getByText('From Date')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    fireEvent.change(fromInput, { target: { value: '2026-05-15' } })

    // May 14 IST < May 15 from-date, so it should be excluded
    await waitFor(() => {
      expect(screen.getByText(/No Findings Match/i)).toBeInTheDocument()
    })
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────

describe('Findings — empty state', () => {
  it('shows empty state when no findings exist', async () => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    renderFindings()
    expect(await screen.findByText(/No Findings Match/i)).toBeInTheDocument()
  })
})
