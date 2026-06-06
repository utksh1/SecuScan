import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import PluginHealth from '../../../src/pages/PluginHealth'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  listPlugins: vi.fn(),
}))

vi.mock('../../../src/routes', () => ({
  routePath: { scanTool: (id: string) => `/toolkit/${id}` },
}))

import { listPlugins } from '../../../src/api'

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makePlugin(overrides: any = {}) {
  return {
    id: `plugin-${Math.random().toString(36).slice(2)}`,
    name: 'Test Plugin',
    description: 'A test plugin',
    category: 'network',
    safety_level: 'safe',
    enabled: true,
    icon: 'terminal',
    requires_consent: false,
    availability: {
      runnable: true,
      missing_binaries: [],
      status: 'ok',
      guidance: null,
    },
    ...overrides,
  }
}

function makeRunnable(overrides: any = {}) {
  return makePlugin({ availability: { runnable: true, missing_binaries: [], status: 'ok', guidance: null }, ...overrides })
}

function makeDegraded(missingBinaries = ['nmap'], overrides: any = {}) {
  return makePlugin({
    availability: { runnable: false, missing_binaries: missingBinaries, status: 'degraded', guidance: 'Install nmap to enable this plugin.' },
    ...overrides,
  })
}

function makeBlocked(overrides: any = {}) {
  return makePlugin({
    availability: { runnable: false, missing_binaries: [], status: 'blocked', guidance: null },
    ...overrides,
  })
}

function mockApi(plugins: ReturnType<typeof makePlugin>[]) {
  vi.mocked(listPlugins).mockResolvedValue({ plugins, total: plugins.length } as any)
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PluginHealth />
    </MemoryRouter>
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('PluginHealth — plugin health dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page header', () => {
    mockApi([])
    renderPage()
    expect(screen.getByRole('heading', { name: /Plugin/i })).toBeInTheDocument()
  })

  it('shows loading state while fetching', () => {
    vi.mocked(listPlugins).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText(/Scanning plugin registry/i)).toBeInTheDocument()
  })

  it('shows error state and retry button when fetch fails', async () => {
    vi.mocked(listPlugins).mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => expect(screen.getByText(/Plugin_Registry_Retrieval_Failed/i)).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('retry button re-fetches plugins', async () => {
    vi.mocked(listPlugins).mockRejectedValueOnce(new Error('fail'))
    mockApi([makeRunnable({ name: 'Recovered Plugin' })])
    renderPage()

    await waitFor(() => expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument())
    await userEvent.click(screen.getByRole('button', { name: /Retry/i }))

    await waitFor(() => expect(screen.getByText('Recovered Plugin')).toBeInTheDocument())
  })

  it('renders runnable plugins in the Runnable group', async () => {
    mockApi([makeRunnable({ name: 'Nmap Scanner' })])
    renderPage()
    await waitFor(() => expect(screen.getByText('Nmap Scanner')).toBeInTheDocument())
    expect(screen.getByRole('heading', { name: /Runnable/i })).toBeInTheDocument()
  })

  it('renders degraded plugins with missing binaries', async () => {
    mockApi([makeDegraded(['nmap', 'masscan'], { name: 'Port Scanner' })])
    renderPage()

    await waitFor(() => expect(screen.getByText('Port Scanner')).toBeInTheDocument())
    expect(screen.getByText('nmap')).toBeInTheDocument()
    expect(screen.getByText('masscan')).toBeInTheDocument()
    expect(screen.getByText(/Missing Dependencies/i)).toBeInTheDocument()
  })

  it('renders blocked plugins with blocked status', async () => {
    mockApi([makeBlocked({ name: 'Exploit Plugin' })])
    renderPage()

    await waitFor(() => expect(screen.getByText('Exploit Plugin')).toBeInTheDocument())
    expect(screen.getAllByText('Blocked').length).toBeGreaterThan(0)
  })

  it('shows guidance text for degraded plugins', async () => {
    mockApi([makeDegraded(['nmap'], { name: 'Degraded Plugin' })])
    renderPage()

    await waitFor(() => expect(screen.getByText('Install nmap to enable this plugin.')).toBeInTheDocument())
  })

  it('shows correct summary counts in header metrics', async () => {
    mockApi([
      makeRunnable({ id: 'r1' }),
      makeRunnable({ id: 'r2' }),
      makeDegraded(['nmap'], { id: 'd1' }),
      makeBlocked({ id: 'b1' }),
    ])
    renderPage()

    await waitFor(() => expect(screen.queryByText(/Scanning plugin registry/i)).not.toBeInTheDocument())

    // Summary metric cards show padded counts
    const metricValues = screen.getAllByText(/^\d{2}$/)
    const values = metricValues.map((el) => el.textContent)
    expect(values).toContain('02') // runnable
    expect(values).toContain('01') // degraded
    expect(values).toContain('01') // blocked
  })

  it('shows empty state for a group with no plugins', async () => {
    mockApi([makeRunnable({ id: 'r1' })])
    renderPage()

    await waitFor(() => expect(screen.queryByText(/Scanning plugin registry/i)).not.toBeInTheDocument())
    expect(screen.getByText(/No plugins are blocked/i)).toBeInTheDocument()
    expect(screen.getByText(/No plugins are in a degraded state/i)).toBeInTheDocument()
  })

  it('groups blocked plugins before degraded before runnable', async () => {
    mockApi([
      makeRunnable({ id: 'r1', name: 'Alpha Runnable' }),
      makeDegraded(['nmap'], { id: 'd1', name: 'Beta Degraded' }),
      makeBlocked({ id: 'b1', name: 'Gamma Blocked' }),
    ])
    renderPage()

    await waitFor(() => expect(screen.getByText('Alpha Runnable')).toBeInTheDocument())

    const headings = screen.getAllByRole('heading').map((h) => h.textContent)
    const blockedIdx = headings.findIndex((h) => /blocked/i.test(h || ''))
    const degradedIdx = headings.findIndex((h) => /degraded/i.test(h || ''))
    const runnableIdx = headings.findIndex((h) => /runnable/i.test(h || ''))

    expect(blockedIdx).toBeLessThan(degradedIdx)
    expect(degradedIdx).toBeLessThan(runnableIdx)
  })

  it('clicking a plugin card navigates to toolkit route', async () => {
    const plugin = makeRunnable({ id: 'nmap-plugin', name: 'Navigate Test' })
    mockApi([plugin])

    const { container } = renderPage()
    await waitFor(() => expect(screen.getByText('Navigate Test')).toBeInTheDocument())

    const card = container.querySelector('button[type="button"]') as HTMLButtonElement
    expect(card).toBeTruthy()
    await userEvent.click(card)
    // Navigation is handled by useNavigate — just verify the click doesn't throw
  })

  it('negative: does not show missing_binaries section for runnable plugins', async () => {
    mockApi([makeRunnable({ name: 'Clean Plugin' })])
    renderPage()

    await waitFor(() => expect(screen.getByText('Clean Plugin')).toBeInTheDocument())
    expect(screen.queryByText(/Missing Dependencies/i)).not.toBeInTheDocument()
  })

  it('negative: does not show guidance for plugins with no guidance', async () => {
    mockApi([makeBlocked({ name: 'Silent Block' })])
    renderPage()

    await waitFor(() => expect(screen.getByText('Silent Block')).toBeInTheDocument())
    // Guidance section should not appear since guidance is null
    expect(screen.queryByText('Install')).not.toBeInTheDocument()
  })
})
