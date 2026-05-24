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

vi.mock('../../../src/hooks/useSavedViews', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../src/hooks/useSavedViews')>()
  return {
    ...actual,
    useSavedViews: () => ({
      views: [],
      loading: false,
      saveView: vi.fn(),
      deleteView: vi.fn(),
      renameView: vi.fn(),
    }),
  }
})

// â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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

// â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function renderFindings() {
  return render(
    <MemoryRouter>
      <Findings />
    </MemoryRouter>,
  )
}

async function waitForLoad() {
  await waitFor(() => {
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
  })
}

function clickSortButton(label: string) {
  fireEvent.click(screen.getByRole('button', { name: new RegExp(label, 'i') }))
}

function getVisibleTitles() {
  return Array.from(document.querySelectorAll('h3'))
    .map((el) => el.textContent ?? '')
    .filter(Boolean)
}

// â”€â”€ Loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” loading state', () => {
  it('shows loading text while fetching', () => {
    vi.mocked(getFindings).mockReturnValue(new Promise(() => {}))
    renderFindings()
    expect(screen.getByText(/Synchronizing findings feed/i)).toBeInTheDocument()
  })
})

// â”€â”€ Severity filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” severity filtering', () => {
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
    const toggle = critButtons.find((btn) => btn.textContent?.trim() === 'Critical')
    expect(toggle).toBeTruthy()
    await user.click(toggle!)

    await waitFor(() => {
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
    }, { timeout: 3000 })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
  })
})

// â”€â”€ Sort options â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” sorting', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('sort controls contain all expected options', async () => {
    renderFindings()
    await waitForLoad()

    expect(screen.getByRole('button', { name: /by severity/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /oldest/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /target alpha/i })).toBeInTheDocument()
  })

  it('switches to flat list when sort is newest', async () => {
    renderFindings()
    await waitForLoad()

    clickSortButton('Newest')

    await waitFor(() => {
      const headers = screen.getAllByText(/in queue/i)
      expect(headers.length).toBe(1)
    })
  })

  it('newest-first puts most recent finding on top', async () => {
    renderFindings()
    await waitForLoad()

    clickSortButton('Newest')

    await waitFor(() => {
      const titles = getVisibleTitles()
      expect(titles.indexOf('Missing Security Headers')).toBeLessThan(titles.indexOf('SQL Injection in Login'))
      expect(titles.indexOf('SQL Injection in Login')).toBeLessThan(titles.indexOf('Stored XSS in Comments'))
    })
  })

  it('oldest-first puts earliest finding on top', async () => {
    renderFindings()
    await waitForLoad()

    clickSortButton('Oldest')

    await waitFor(() => {
      const titles = getVisibleTitles()
      expect(titles.indexOf('Stored XSS in Comments')).toBeLessThan(titles.indexOf('SQL Injection in Login'))
      expect(titles.indexOf('SQL Injection in Login')).toBeLessThan(titles.indexOf('Missing Security Headers'))
    })
  })

  it('target A-Z sorts alphabetically by target', async () => {
    renderFindings()
    await waitForLoad()

    clickSortButton('Target Alpha')

    await waitFor(() => {
      const titles = getVisibleTitles()
      const webIdx = titles.indexOf('Stored XSS in Comments')
      const apiIdx = titles.indexOf('SQL Injection in Login')
      expect(apiIdx).toBeLessThan(webIdx)
    })
  })
})

// â”€â”€ Target filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” target filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('renders unique targets in dropdown', async () => {
    renderFindings()
    await waitForLoad()

    const targetSelect = screen.getByDisplayValue(/All targets/i)
    const options = within(targetSelect as HTMLElement).getAllByRole('option')
    const labels = options.map((o) => o.textContent)

    expect(labels).toContain('api.example.com')
    expect(labels).toContain('web.example.com')
  })

  it('filters findings when a specific target is selected', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const targetSelect = screen.getByDisplayValue(/All targets/i)
    await user.selectOptions(targetSelect, 'web.example.com')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
  })
})

// â”€â”€ Scanner / tool filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” scanner filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('renders unique scanners in dropdown', async () => {
    renderFindings()
    await waitForLoad()

    const scannerSelect = screen.getByDisplayValue(/All scanners/i)
    const options = within(scannerSelect as HTMLElement).getAllByRole('option')
    const labels = options.map((o) => o.textContent)

    expect(labels).toContain('sqlmap')
    expect(labels).toContain('zap')
    expect(labels).toContain('nikto')
  })

  it('filters findings to one scanner', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const scannerSelect = screen.getByDisplayValue(/All scanners/i)
    await user.selectOptions(scannerSelect, 'zap')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
      expect(screen.queryByText('Missing Security Headers')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
  })
})

// â”€â”€ Date range filter â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” date range filter', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('filters out findings before the from-date', async () => {
    renderFindings()
    await waitForLoad()

    const fromLabel = screen.getByText('Discovered From')
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

    const toLabel = screen.getByText('Discovered To')
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

    const fromLabel = screen.getByText('Discovered From')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    const toLabel = screen.getByText('Discovered To')
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

// â”€â”€ Reset filters â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” reset filters', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('clears all active filters when severity All is clicked', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    const targetSelect = screen.getByDisplayValue(/All targets/i)
    await user.selectOptions(targetSelect, 'web.example.com')

    await waitFor(() => {
      expect(screen.queryByText('SQL Injection in Login')).not.toBeInTheDocument()
    })

    await user.selectOptions(screen.getByDisplayValue(/web\.example\.com/i), 'all')

    await waitFor(() => {
      expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
      expect(screen.getAllByText('Stored XSS in Comments').length).toBeGreaterThanOrEqual(1)
    })
  })
})



// â”€â”€ Active filter summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
describe('Findings â€” active filter summary', () => {
  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: allFindings })
  })

  it('is hidden when no filters are active', async () => {
    renderFindings()
    await waitForLoad()
    expect(screen.queryByLabelText('active filters')).not.toBeInTheDocument()
  })

  it('shows target + scanner chips when both filters are applied', async () => {
    const user = userEvent.setup()
    renderFindings()
    await waitForLoad()

    await user.selectOptions(screen.getByDisplayValue(/All targets/i), 'api.example.com')
    await user.selectOptions(screen.getByDisplayValue(/All scanners/i), 'sqlmap')

    await waitFor(() => {
      expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
    })
  })

  it('shows date range chips when both dates are set', async () => {
    renderFindings()
    await waitForLoad()

    const fromInput = screen.getByText('Discovered From').parentElement!.querySelector('input')!
    const toInput = screen.getByText('Discovered To').parentElement!.querySelector('input')!

    fireEvent.change(fromInput, { target: { value: '2026-05-14' } })
    fireEvent.change(toInput, { target: { value: '2026-05-15' } })

    await waitFor(() => {
      expect(screen.queryByText('Stored XSS in Comments')).not.toBeInTheDocument()
    })
    expect(screen.getAllByText('SQL Injection in Login').length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText('Missing Security Headers').length).toBeGreaterThanOrEqual(1)
  })
})
// â”€â”€ Timezone boundary regression â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

describe('Findings â€” date range respects display timezone', () => {
  const tzBoundaryFinding = {
    id: 'finding-tz-edge',
    severity: 'high',
    category: 'xss',
    title: 'TZ Boundary XSS',
    target: 'tz.example.com',
    description: 'Edge case across UTC day boundary.',
    remediation: 'Fix it.',
    discovered_at: '2026-05-13T20:00:00Z',
    plugin_id: 'zap',
  }

  beforeEach(() => {
    vi.mocked(getFindings).mockResolvedValue({ findings: [tzBoundaryFinding] })
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

    const fromLabel = screen.getByText('Discovered From')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    fireEvent.change(fromInput, { target: { value: '2026-05-14' } })

    await waitFor(() => {
      expect(screen.getAllByText('TZ Boundary XSS').length).toBeGreaterThanOrEqual(1)
    })
  })

  it('excludes the finding when from-date is May-15 in IST', async () => {
    renderFindings()

    await waitFor(() => {
      expect(screen.getAllByText('TZ Boundary XSS').length).toBeGreaterThanOrEqual(1)
    })

    const fromLabel = screen.getByText('Discovered From')
    const fromInput = fromLabel.parentElement!.querySelector('input')!
    fireEvent.change(fromInput, { target: { value: '2026-05-15' } })

    await waitFor(() => {
      expect(screen.getByText(/Queue Cleared/i)).toBeInTheDocument()
    })
  })
})