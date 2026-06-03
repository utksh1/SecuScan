import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Scans from '../../../src/pages/Scans'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  API_BASE: 'http://localhost:5000',
  deleteTask: vi.fn().mockResolvedValue({}),
  clearAllTasks: vi.fn().mockResolvedValue({}),
  bulkDeleteTasks: vi.fn().mockResolvedValue({}),
}))

vi.mock('../../../src/routes', () => ({
  routePath: { task: (id: string) => `/task/${id}` },
}))

vi.mock('../../../src/utils/date', () => ({
  parseDateSafe: (d: any) => new Date(d || Date.now()),
  formatLocaleDate: () => '2024-01-01',
  formatLocaleTime: () => '12:00',
}))

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { configurable: true, value: 800 })
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })

// ── Fixtures ─────────────────────────────────────────────────────────────────

function makeTask(overrides: any = {}) {
  const id = overrides.task_id ?? `task-${Math.random().toString(36).slice(2)}`
  return {
    task_id: id,
    plugin_id: 'nmap',
    tool: 'nmap',
    target: 'example.com',
    status: 'completed' as const,
    created_at: '2024-01-01T00:00:00Z',
    duration_seconds: 30,
    ...overrides,
  }
}

function makeLargeFetch(count: number) {
  return Array.from({ length: count }, (_, i) => makeTask({ task_id: `task-${i}`, tool: `tool-${i}` }))
}

function mockFetch(tasks: ReturnType<typeof makeTask>[]) {
  global.fetch = vi.fn().mockResolvedValue({
    json: () => Promise.resolve({ tasks }),
  } as any)
}

function renderScans() {
  return render(
    <MemoryRouter>
      <Scans />
    </MemoryRouter>
  )
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('Scans — virtualized task list', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the page header', () => {
    mockFetch([])
    renderScans()
    // Use heading role to avoid matching both the badge and the h1
    expect(screen.getByRole('heading', { name: /Operational/i })).toBeInTheDocument()
  })

  it('shows empty state when there are no tasks', async () => {
    mockFetch([])
    renderScans()
    await waitFor(() => expect(screen.getByText(/Archive Isolated/i)).toBeInTheDocument())
  })

  it('renders task cards for loaded tasks', async () => {
    const tasks = [makeTask({ tool: 'nmap', target: 'target.com' })]
    mockFetch(tasks)
    renderScans()
    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())
    expect(screen.getByText('target.com')).toBeInTheDocument()
  })

  it('does not mount all cards to DOM with 300 tasks (DOM bloat test)', async () => {
    const tasks = makeLargeFetch(300)
    mockFetch(tasks)
    const { container } = renderScans()

    await waitFor(() => expect(screen.queryByText(/Archive Isolated/i)).not.toBeInTheDocument(), { timeout: 3000 })

    const cards = container.querySelectorAll('.group\\/card')
    expect(cards.length).toBeLessThan(40)
  })

  it('status filter buttons are rendered and clickable', async () => {
    mockFetch([])
    renderScans()
    const allBtn = screen.getByRole('button', { name: /ALL_OPERATIONS/i })
    expect(allBtn).toBeInTheDocument()
    await userEvent.click(allBtn)
  })

  it('selecting a task adds it to selectedIds (checkbox toggles)', async () => {
    const tasks = [makeTask({ task_id: 'task-1', tool: 'nuclei' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nuclei')).toBeInTheDocument())

    // Checkbox has aria-label="add" (material icon name) — use getAllByRole and pick first
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])

    await waitFor(() => expect(screen.getByText(/Records_Selected_For_Pruning/i)).toBeInTheDocument())
  })

  it('select-all selects all tasks', async () => {
    const tasks = [makeTask({ task_id: 'task-1' }), makeTask({ task_id: 'task-2' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getAllByText(/nmap/i).length).toBeGreaterThan(0))

    await userEvent.click(screen.getByRole('button', { name: /Select_All/i }))

    await waitFor(() => {
      const count = screen.getByText('2')
      expect(count).toBeInTheDocument()
    })
  })

  it('cancel clears selection', async () => {
    const tasks = [makeTask({ task_id: 'task-1' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    // Select the task via checkbox
    const checkboxes = screen.getAllByRole('checkbox')
    await userEvent.click(checkboxes[0])
    await waitFor(() => expect(screen.getByText(/Records_Selected_For_Pruning/i)).toBeInTheDocument())

    // Cancel — selectedIds should clear, checkbox returns to unchecked
    await userEvent.click(screen.getByRole('button', { name: /Cancel/i }))
    await waitFor(() =>
      expect(checkboxes[0]).toHaveAttribute('aria-checked', 'false')
    )
  })

  it('polls every 5 seconds', async () => {
    mockFetch([])
    renderScans()

    expect(global.fetch).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5000)
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2))
  })

  it('negative: Delete_Record button NOT shown for running tasks', async () => {
    const tasks = [makeTask({ status: 'running' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await userEvent.click(screen.getByText('nmap').closest('[class*="cursor-pointer"]')!)

    expect(screen.queryByText('Delete_Record')).not.toBeInTheDocument()
  })

  it('negative: bulk delete not triggered with empty selection', async () => {
    mockFetch([makeTask()])
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    const { bulkDeleteTasks } = await import('../../../src/api')
    expect(bulkDeleteTasks).not.toHaveBeenCalled()
  })
})
