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
// function getSortSelect() {
//   const label = screen.getByText('Sort By')
//   return label.parentElement!.querySelector('select')!
// }

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

// ── Empty state ───────────────────────────────────────────────────────────────

describe('Findings — empty state', () => {
  it('shows empty state when no findings exist', async () => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [] })
    renderFindings()
    expect(await screen.findByText(/No Findings Match/i)).toBeInTheDocument()
  })
})

// ── Search filter ─────────────────────────────────────────────────────────────

describe('Findings — search filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('filters findings by search query across fields', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const searchInput = screen.getByPlaceholderText(/Title, target, CVE, remediation/i)
    await user.type(searchInput, 'web.example')

    await waitFor(() => {
      expect(screen.queryByText(/SQL Injection in Login/i)).not.toBeInTheDocument()
    })
    expect(screen.getAllByText(/Stored XSS in Comments/i).length).toBeGreaterThanOrEqual(1)
  })
})
