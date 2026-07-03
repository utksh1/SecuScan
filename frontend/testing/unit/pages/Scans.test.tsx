import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Scans from '../../../src/pages/Scans'

// ── Mocks ────────────────────────────────────────────────────────────────────

vi.mock('../../../src/api', () => ({
  API_BASE: 'http://localhost:5000',
  deleteTask: vi.fn().mockResolvedValue({}),
  clearAllTasks: vi.fn().mockResolvedValue({}),
  bulkDeleteTasks: vi.fn().mockResolvedValue({}),
  startTask: vi.fn().mockResolvedValue({ task_id: 'new-task-123' }),
}))

vi.mock('../../../src/routes', () => ({
  routePath: { task: (id: string) => `/task/${id}` },
}))

vi.mock('../../../src/utils/date', () => ({
  parseDateSafe: (d: any) => new Date(d || Date.now()),
  formatLocaleDate: () => '2024-01-01',
  formatLocaleTime: () => '12:00',
}))

vi.mock('../../../src/components/ConfirmModal', () => ({
  ConfirmModal: ({ isOpen, onConfirm, title }: any) =>
    isOpen ? (
      <div>
        <span>{title}</span>
        <button onClick={onConfirm}>Confirm</button>
      </div>
    ) : null,
}))

vi.mock('../../../src/components/Pagination', () => ({
  default: ({ page, onNext, onPrev }: any) => (
    <div>
      <button onClick={onPrev}>Prev</button>
      <span>Page {page}</span>
      <button onClick={onNext}>Next</button>
    </div>
  ),
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

function mockFetch(tasks: ReturnType<typeof makeTask>[], total?: number) {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({
      tasks,
      pagination: { total_items: total ?? tasks.length },
    }),
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

describe('Scans — task list', () => {
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

  it('status filter buttons are rendered and clickable', async () => {
    mockFetch([])
    renderScans()
    const allBtn = screen.getByRole('button', { name: /ALL_OPERATIONS/i })
    expect(allBtn).toBeInTheDocument()
    await userEvent.click(allBtn)
  })

  it('select-all selects all tasks', async () => {
    const tasks = [makeTask({ task_id: 'task-1' }), makeTask({ task_id: 'task-2' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getAllByText(/nmap/i).length).toBeGreaterThan(0))

    await userEvent.click(screen.getByRole('button', { name: /Select_All/i }))

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument()
    })
  })

  it('cancel clears selection', async () => {
    const tasks = [makeTask({ task_id: 'task-1' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /Select_All/i }))
    await waitFor(() => expect(screen.getByText(/Records_Selected_For_Pruning/i)).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /Cancel/i }))

    await waitFor(() => {
      const selectAllBtn = screen.getByRole('button', { name: /Select_All/i })
      expect(selectAllBtn.className).not.toContain('bg-rag-blue')
    })
  })

  it('polls every 5 seconds', async () => {
    mockFetch([])
    renderScans()

    expect(global.fetch).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(5000)
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2))
  })

  it('shows pagination when total exceeds page limit', async () => {
    const tasks = Array.from({ length: 10 }, (_, i) => makeTask({ task_id: `task-${i}` }))
    mockFetch(tasks, 25)
    renderScans()

    await waitFor(() => expect(screen.getAllByText(/nmap/i).length).toBeGreaterThan(0))
    expect(screen.getByText(/Page 1/i)).toBeInTheDocument()
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

  it('shows confirm modal when deleting a task', async () => {
    const tasks = [makeTask({ task_id: 'task-1', status: 'completed' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await userEvent.click(screen.getByText('nmap').closest('[class*="cursor-pointer"]')!)
    await waitFor(() => expect(screen.getByText('Delete_Record')).toBeInTheDocument())

    await userEvent.click(screen.getByText('Delete_Record'))

    await waitFor(() => expect(screen.getByText('Delete Scan Record')).toBeInTheDocument())
  })

  it('renders quick re-run button for completed tasks and triggers handleRescan', async () => {
    const tasks = [makeTask({ task_id: 'task-123', status: 'completed', tool: 'nmap' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    const rerunBtn = screen.getByRole('button', { name: /Re-run nmap scan/i })
    expect(rerunBtn).toBeInTheDocument()

    const { startTask } = await import('../../../src/api')
    await userEvent.click(rerunBtn)

    await waitFor(() => {
      expect(startTask).toHaveBeenCalledWith(
        'nmap',
        expect.any(Object),
        true,
        undefined,
        undefined
      )
    })
  })

  it('handles clearAllTasks failure correctly', async () => {
    const { clearAllTasks } = await import('../../../src/api')
    vi.mocked(clearAllTasks).mockRejectedValueOnce(new Error('Purge failed'))

    const tasks = [makeTask({ task_id: 'task-1', tool: 'nmap' })]
    mockFetch(tasks)
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await userEvent.click(screen.getByRole('button', { name: /Select_All/i }))
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument()
    })

    const purgeBtn = screen.getByRole('button', { name: /Purge_All_Records/i })
    await userEvent.click(purgeBtn)

    expect(screen.getByText('CRITICAL OPERATION')).toBeInTheDocument()

    const confirmBtn = screen.getByRole('button', { name: /Confirm/i })
    await userEvent.click(confirmBtn)

    // Assert error feedback is shown in-app
    await waitFor(() => {
      const alertEl = screen.getByRole('alert')
      expect(alertEl).toBeInTheDocument()
      expect(alertEl).toHaveTextContent('Failed to clear history. Ensure no tasks are currently running.')
    })

    // Assert tasks and selection state are not incorrectly cleared
    expect(screen.getByText('nmap')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()

    // Test that the error banner can be closed
    const closeBtn = screen.getByRole('button', { name: /Close alert/i })
    await userEvent.click(closeBtn)

    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })
})
