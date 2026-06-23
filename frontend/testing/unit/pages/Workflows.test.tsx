import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Workflows from '../../../src/pages/Workflows'
import { getWorkflows, createWorkflow, runWorkflow, updateWorkflow, deleteWorkflow } from '../../../src/api'
import { ToastProvider } from '../../../src/components/ToastContext'

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
  schedule_seconds: 3600,
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
    <ToastProvider>
      <MemoryRouter>
        <Workflows />
      </MemoryRouter>
    </ToastProvider>
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
    expect(screen.getAllByText('Every 1h').length).toBeGreaterThan(0)
  })

  it('shows step count', async () => {
    renderPage()
    await screen.findByText('Nightly Scan')
    expect(screen.getAllByText('1').length).toBeGreaterThan(0)
  })
})

describe('Workflows — create action', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([])
    vi.mocked(createWorkflow).mockResolvedValue(mockWorkflow)
  })

  it('creates workflow with schedule_seconds payload', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(/No Workflows/i)

    await user.click(screen.getAllByRole('button', { name: /New Workflow/i })[0])
    await user.type(screen.getByPlaceholderText('My Workflow'), 'Nightly Scan')
    await user.clear(screen.getByPlaceholderText('3600'))
    await user.type(screen.getByPlaceholderText('3600'), '7200')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(vi.mocked(createWorkflow)).toHaveBeenCalledWith({
      name: 'Nightly Scan',
      schedule_seconds: 7200,
      enabled: true,
      steps: [{
        plugin_id: '',
        inputs: {},
        execution_context: {
          scan_profile: 'standard',
          validation_mode: 'proof',
          evidence_level: 'standard',
        },
      }],
    })
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

describe('Workflows — create validation: invalid JSON', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([])
    vi.mocked(createWorkflow).mockResolvedValue(mockWorkflow)
    vi.mocked(createWorkflow).mockClear()
  })

  it('shows inline JSON error when steps field contains malformed JSON', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(/No Workflows/i)

    await user.click(screen.getAllByRole('button', { name: /New Workflow/i })[0])

    const textarea = document.querySelector('textarea') as HTMLTextAreaElement
    await user.clear(textarea)
    await user.type(textarea, '{{ not valid json }}}')

    await user.type(screen.getByPlaceholderText('My Workflow'), 'Bad Workflow')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(screen.getByText('Invalid JSON in steps field')).toBeInTheDocument()
    expect(vi.mocked(createWorkflow)).not.toHaveBeenCalled()
  })

  it('clears the JSON error when the steps textarea is edited', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(/No Workflows/i)

    await user.click(screen.getAllByRole('button', { name: /New Workflow/i })[0])

    const textarea = document.querySelector('textarea') as HTMLTextAreaElement
    await user.clear(textarea)
    await user.type(textarea, '{{ bad }')
    await user.type(screen.getByPlaceholderText('My Workflow'), 'X')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))
    expect(screen.getByText('Invalid JSON in steps field')).toBeInTheDocument()

    // Now fix the textarea — error should disappear
    await user.clear(textarea)
    await user.type(textarea, '[[]]')
    expect(screen.queryByText('Invalid JSON in steps field')).not.toBeInTheDocument()
  })
})

describe('Workflows — create validation: schedule input', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([])
    vi.mocked(createWorkflow).mockResolvedValue(mockWorkflow)
    vi.mocked(createWorkflow).mockClear()
  })

  async function openCreateSheet() {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText(/No Workflows/i)
    await user.click(screen.getAllByRole('button', { name: /New Workflow/i })[0])
    await user.type(screen.getByPlaceholderText('My Workflow'), 'Test')
    return user
  }

  it('shows error for a negative schedule value', async () => {
    const user = await openCreateSheet()
    const scheduleInput = screen.getByPlaceholderText('3600')
    await user.clear(scheduleInput)
    await user.type(scheduleInput, '-60')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(screen.getByText(/Schedule must be a positive whole number/i)).toBeInTheDocument()
    expect(vi.mocked(createWorkflow)).not.toHaveBeenCalled()
  })

  it('shows error for a zero schedule value', async () => {
    const user = await openCreateSheet()
    const scheduleInput = screen.getByPlaceholderText('3600')
    await user.clear(scheduleInput)
    await user.type(scheduleInput, '0')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(screen.getByText(/Schedule must be a positive whole number/i)).toBeInTheDocument()
    expect(vi.mocked(createWorkflow)).not.toHaveBeenCalled()
  })

  it('shows error for a fractional schedule value', async () => {
    const user = await openCreateSheet()
    const scheduleInput = screen.getByPlaceholderText('3600')
    await user.clear(scheduleInput)
    await user.type(scheduleInput, '1.5')
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(screen.getByText(/Schedule must be a positive whole number/i)).toBeInTheDocument()
    expect(vi.mocked(createWorkflow)).not.toHaveBeenCalled()
  })

  it('submits successfully when schedule is left empty (manual mode)', async () => {
    const user = await openCreateSheet()
    const scheduleInput = screen.getByPlaceholderText('3600')
    await user.clear(scheduleInput)  // empty = null = manual
    await user.click(screen.getByRole('button', { name: /^Create$/i }))

    expect(vi.mocked(createWorkflow)).toHaveBeenCalledWith(
      expect.objectContaining({ schedule_seconds: null })
    )
  })
})

describe('Workflows — toggle: both directions and UI state', () => {
  beforeEach(() => {
    vi.mocked(updateWorkflow).mockClear()
  })

  it('reflects disabled state in badge after toggling an enabled workflow off', async () => {
    const user = userEvent.setup()
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])       // enabled: true
    vi.mocked(updateWorkflow).mockResolvedValue({ ...mockWorkflow, enabled: false })

    renderPage()
    await screen.findByText('Nightly Scan')

    // Before toggle: Enabled badge present, Disable button present
    expect(screen.getByText('Enabled')).toBeInTheDocument()
    expect(screen.getByTitle('Disable')).toBeInTheDocument()

    await user.click(screen.getByTitle('Disable'))
    expect(vi.mocked(updateWorkflow)).toHaveBeenCalledWith(mockWorkflow.id, { enabled: false })

    // After toggle: badge switches to Disabled, button title flips to Enable
    await waitFor(() => {
      expect(screen.getByText('Disabled')).toBeInTheDocument()
      expect(screen.getByTitle('Enable')).toBeInTheDocument()
    })
  })

  it('reflects enabled state in badge after toggling a disabled workflow on', async () => {
    const user = userEvent.setup()
    vi.mocked(getWorkflows).mockResolvedValue([disabledWorkflow])   // enabled: false
    vi.mocked(updateWorkflow).mockResolvedValue({ ...disabledWorkflow, enabled: true })

    renderPage()
    await screen.findByText('Disabled Scan')

    expect(screen.getByText('Disabled')).toBeInTheDocument()
    expect(screen.getByTitle('Enable')).toBeInTheDocument()

    await user.click(screen.getByTitle('Enable'))
    expect(vi.mocked(updateWorkflow)).toHaveBeenCalledWith(disabledWorkflow.id, { enabled: true })

    await waitFor(() => {
      expect(screen.getByText('Enabled')).toBeInTheDocument()
      expect(screen.getByTitle('Disable')).toBeInTheDocument()
    })
  })

  it('disables the toggle button while the API call is in flight', async () => {
    const user = userEvent.setup()
    let resolve!: (v: typeof mockWorkflow) => void
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(updateWorkflow).mockReturnValue(new Promise(r => { resolve = r }))

    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Disable'))

    // Button should be disabled while awaiting
    expect(screen.getByTitle('Disable')).toBeDisabled()

    // Resolve and confirm it re-enables
    resolve({ ...mockWorkflow, enabled: false })
    await waitFor(() => expect(screen.getByTitle('Enable')).not.toBeDisabled())
  })
})

describe('Workflows — delete action', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(deleteWorkflow).mockResolvedValue({ deleted: true })
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

describe('Workflows — delete: dialog state machine', () => {
  beforeEach(() => {
    vi.mocked(getWorkflows).mockResolvedValue([mockWorkflow])
    vi.mocked(deleteWorkflow).mockClear()
  })

  it('shows "Deleting..." and disables buttons while delete is in flight', async () => {
    const user = userEvent.setup()
    let resolve!: (v: { deleted: boolean }) => void
    vi.mocked(deleteWorkflow).mockReturnValue(new Promise(r => { resolve = r }))

    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))

    const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i })
    await user.click(deleteButtons[deleteButtons.length - 1])

    // Loading state: button text changes, both buttons disabled
    expect(screen.getByText('Deleting...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Cancel/i })).toBeDisabled()

    resolve({ deleted: true })
    await waitFor(() => {
      expect(screen.queryByText('Nightly Scan')).not.toBeInTheDocument()
    })
  })

  it('keeps the dialog open and workflow in list when deleteWorkflow rejects', async () => {
    const user = userEvent.setup()
    vi.mocked(deleteWorkflow).mockRejectedValue(new Error('Server error'))

    renderPage()
    await screen.findByText('Nightly Scan')
    await user.click(screen.getByTitle('Delete'))

    const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i })
    await user.click(deleteButtons[deleteButtons.length - 1])

    // After the rejection: dialog stays, workflow still visible
    await waitFor(() => {
      expect(screen.getByText('Delete Workflow')).toBeInTheDocument()
      const headings = screen.getAllByRole('heading')
      const workflowHeading = headings.find(h => h.textContent?.includes('Nightly Scan'))
      expect(workflowHeading).toBeInTheDocument()
    })
  })
})
