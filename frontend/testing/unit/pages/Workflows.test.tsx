import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Workflows from '../../../src/pages/Workflows'
import { getWorkflows, runWorkflow, updateWorkflow, deleteWorkflow } from '../../../src/api'

vi.mock('../../../src/api', () => ({
  getWorkflows: vi.fn(),
  createWorkflow: vi.fn(),
  runWorkflow: vi.fn(),
  updateWorkflow: vi.fn(),
  deleteWorkflow: vi.fn(),
}))

const mockWorkflow = {
  id: 'wf-001',
  name: 'Nightly Scan',
  schedule_interval: '0 0 * * *',
  enabled: true,
  steps: [{ plugin_id: 'nmap', inputs: {} }],
  last_run_at: null,
  queued_task_ids: [],
}

const disabledWorkflow = {
  ...mockWorkflow,
  id: 'wf-002',
  name: 'Disabled Scan',
  enabled: false,
}

function renderPage() {
  return render(
    <MemoryRouter>
      <Workflows />
    </MemoryRouter>
  )
}

describe('Workflows — loading and empty states', () => {
    beforeEach(() => {
    vi.mocked(getWorkflows).mockClear()
})

  it('shows loading spinner while fetching', () => {
    vi.mocked(getWorkflows).mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText(/Loading Workflows/i)).toBeInTheDocument()
  })

  it('shows empty state when no workflows exist', async () => {
  vi.mocked(getWorkflows).mockResolvedValue([])
  renderPage()
  expect(await screen.findByText(/No Workflows/i)).toBeInTheDocument()
  expect(screen.getByText(/Create a workflow to automate recurring scans/i)).toBeInTheDocument()
  })

  it('shows error state when fetch fails', async () => {
  vi.mocked(getWorkflows).mockRejectedValue(new Error('Network error'))
  renderPage()
  expect(await screen.findByText('Failed to load')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument()
  })

  it('retries fetch when retry button is clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(getWorkflows).mockRejectedValue(new Error('Network error'))
    renderPage()
    await screen.findByRole('button', { name: /Retry/i })
    await user.click(screen.getByRole('button', { name: /Retry/i }))
    expect(vi.mocked(getWorkflows)).toHaveBeenCalledTimes(2)
  })
})

describe('Workflows — listing', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow, disabledWorkflow])
  })

  it('renders workflow cards', async () => {
    renderPage()
    expect(await screen.findByText('Nightly Scan')).toBeInTheDocument()
    expect(screen.getByText('Disabled Scan')).toBeInTheDocument()
  })

  it('shows enabled badge for enabled workflow', async () => {
    renderPage()
    await screen.findByText('Nightly Scan')
    const badges = screen.getAllByText('Enabled')
    expect(badges.length).toBeGreaterThan(0)
  })

  it('shows disabled badge for disabled workflow', async () => {
    renderPage()
    await screen.findByText('Disabled Scan')
    expect(screen.getByText('Disabled')).toBeInTheDocument()
  })

  it('shows schedule interval', async () => {
    renderPage()
    await screen.findByText('Nightly Scan')
    expect(screen.getAllByText('0 0 * * *').length).toBeGreaterThan(0)
  })

  it('shows step count', async () => {
    renderPage()
    await screen.findByText('Nightly Scan')
    expect(screen.getAllByText('1').length).toBeGreaterThan(0)
  })
})

describe('Workflows — run action', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(runWorkflow).mockResolvedValue({ queued_task_ids: ['task-123'] })
  })

  it('calls runWorkflow with correct id when run button clicked', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Run now'))
    expect(vi.mocked(runWorkflow)).toHaveBeenCalledWith(mockWorkflow.id)
  })
})

describe('Workflows — toggle action', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(updateWorkflow).mockResolvedValue({ ...mockWorkflow, enabled: false })
  })

  it('calls updateWorkflow with toggled enabled state', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Disable'))
    expect(vi.mocked(updateWorkflow)).toHaveBeenCalledWith(mockWorkflow.id, { enabled: false })
  })
})

describe('Workflows — delete action', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(deleteWorkflow).mockResolvedValue({ deleted: true } as any)
    vi.mocked(deleteWorkflow).mockClear()
  })

  it('shows confirmation dialog when delete clicked', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))
    expect(screen.getByText(/Delete Workflow/i)).toBeInTheDocument()
    expect(screen.getByText(/This cannot be undone/i)).toBeInTheDocument()
  })

  it('calls deleteWorkflow when confirmed', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))
    const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i })
    await user.click(deleteButtons[deleteButtons.length - 1])
    expect(vi.mocked(deleteWorkflow)).toHaveBeenCalledWith(mockWorkflow.id)
  })

  it('removes workflow from list after deletion', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))
    const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i })
    await user.click(deleteButtons[deleteButtons.length - 1])
    await waitFor(() => {
      expect(screen.queryByText('Nightly Scan')).not.toBeInTheDocument()
    })
  })

  it('cancels deletion when cancel button clicked', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))
    await user.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(vi.mocked(deleteWorkflow)).not.toHaveBeenCalled()
    expect(screen.getByText('Nightly Scan')).toBeInTheDocument()
  })
})