import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import TaskDetails from '../../../src/pages/TaskDetails'
import { getTaskStatus, getTaskResult, getPluginSchema } from '../../../src/api'
import { useTaskSubscription } from '../../../src/hooks/useTaskSubscription'

vi.mock('../../../src/api', () => ({
  getTaskStatus: vi.fn(),
  getTaskResult: vi.fn(),
  getPluginSchema: vi.fn(),
  startTask: vi.fn(),
  API_BASE: 'http://127.0.0.1:8000',
}))

vi.mock('../../../src/hooks/useTaskSubscription', () => ({
  useTaskSubscription: vi.fn(),
}))

vi.mock('../../../src/components/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

const baseTask = {
  task_id: 'task-1',
  plugin_id: 'nmap',
  tool: 'nmap',
  target: 'example.com',
  status: 'failed',
  created_at: '2026-05-14T10:00:00Z',
  started_at: '2026-05-14T10:00:00Z',
  completed_at: '2026-05-14T10:05:00Z',
  exit_code: 1,
  error_message: 'X'.repeat(600),
}

function renderTaskDetails() {
  return render(
    <MemoryRouter initialEntries={['/task/task-1']}>
      <Routes>
        <Route path="/task/:taskId" element={<TaskDetails />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.mocked(getTaskStatus).mockResolvedValue(baseTask)
  vi.mocked(getTaskResult).mockResolvedValue(null)
  vi.mocked(getPluginSchema).mockResolvedValue({ fields: [], presets: {} } as any)
  vi.mocked(useTaskSubscription).mockImplementation(() => ({} as any))
})

describe('TaskDetails — collapsible error output', () => {
  it('collapses long error_message and shows an expand control', async () => {
    renderTaskDetails()

    const expandBtn = await screen.findByRole('button', { name: /expand error output/i })
    expect(expandBtn).toBeInTheDocument()
    expect(expandBtn).toHaveAttribute('aria-expanded', 'false')
  })

  it('expands the error output when the expand button is clicked', async () => {
    const user = (await import('@testing-library/user-event')).default.setup()
    renderTaskDetails()

    const expandBtn = await screen.findByRole('button', { name: /expand error output/i })
    await user.click(expandBtn)

    expect(screen.getByRole('button', { name: /collapse error output/i })).toHaveAttribute('aria-expanded', 'true')
  })

  it('does not show an expand control for short error_message', async () => {
    vi.mocked(getTaskStatus).mockResolvedValue({ ...baseTask, error_message: 'short error' })
    renderTaskDetails()

    await screen.findByText('short error')
    expect(screen.queryByRole('button', { name: /expand error output/i })).not.toBeInTheDocument()
  })
})