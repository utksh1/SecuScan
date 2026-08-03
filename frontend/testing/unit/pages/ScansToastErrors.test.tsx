import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { ToastProvider } from '../../../src/components/ToastContext'
import Scans from '../../../src/pages/Scans'
import { deleteTask, clearAllTasks, bulkDeleteTasks, startTask } from '../../../src/api'

vi.mock('../../../src/api', async () => {
  const actual: any = await vi.importActual('../../../src/api')
  return {
    ...actual,
    deleteTask: vi.fn(),
    clearAllTasks: vi.fn(),
    bulkDeleteTasks: vi.fn(),
    startTask: vi.fn(),
  }
})

function makeTask(overrides = {}) {
  return {
    task_id: 'task-1',
    plugin_id: 'nmap',
    tool: 'nmap',
    target: 'example.com',
    status: 'completed',
    created_at: '2026-05-14T10:00:00Z',
    ...overrides,
  }
}

function mockFetch(tasks: any[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ tasks, pagination: { total_items: tasks.length } }),
    }),
  )
}

function renderScans() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <Scans />
      </ToastProvider>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  mockFetch([makeTask()])
})

afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
})

describe('Scans — toast error feedback', () => {
  it('shows a toast when clear all tasks fails', async () => {
    vi.mocked(clearAllTasks).mockRejectedValueOnce(new Error('clear failed'))
    const user = userEvent.setup()
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Purge_All_Records/i }))
    const confirmBtn = await screen.findByRole('button', { name: /Confirm/i })
    await user.click(confirmBtn)

    await waitFor(() => {
      expect(screen.getByText(/Failed to clear history/i)).toBeInTheDocument()
    })
  })

  it('shows a toast when bulk delete fails', async () => {
    vi.mocked(bulkDeleteTasks).mockRejectedValueOnce(new Error('bulk failed'))
    const user = userEvent.setup()
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Select_All/i }))
    await waitFor(() => expect(screen.getByText('1')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Prune_Selected_Records/i }))
    const confirmBtn = await screen.findByRole('button', { name: /Confirm/i })
    await user.click(confirmBtn)

    await waitFor(() => {
      expect(screen.getByText(/Failed to delete some tasks/i)).toBeInTheDocument()
    })
  })

  it('shows a toast when rescan fails', async () => {
    vi.mocked(startTask).mockRejectedValueOnce(new Error('rescan failed'))
    const user = userEvent.setup()
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    const rescanBtn = screen.getByRole('button', { name: /Re-run nmap scan/i })
    await user.click(rescanBtn)

    await waitFor(() => {
      expect(screen.getByText(/Rescan failed/i)).toBeInTheDocument()
    })
  })

  it('does not show the old error banner after a failure', async () => {
    vi.mocked(clearAllTasks).mockRejectedValueOnce(new Error('clear failed'))
    const user = userEvent.setup()
    renderScans()

    await waitFor(() => expect(screen.getByText('nmap')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /Purge_All_Records/i }))
    const confirmBtn = await screen.findByRole('button', { name: /Confirm/i })
    await user.click(confirmBtn)

    await waitFor(() => {
      expect(screen.getByText(/Failed to clear history/i)).toBeInTheDocument()
    })

    expect(screen.queryByRole('button', { name: /Close alert/i })).not.toBeInTheDocument()
  })
})
