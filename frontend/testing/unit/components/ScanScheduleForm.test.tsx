import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi } from 'vitest'
import ScanScheduleForm from '../../../src/components/ScanScheduleForm'

describe('ScanScheduleForm', () => {
  const mockOnSubmit = vi.fn().mockResolvedValue(undefined)
  const mockOnCancel = vi.fn()

  beforeEach(() => {
    mockOnSubmit.mockClear()
    mockOnCancel.mockClear()
    mockOnSubmit.mockResolvedValue(undefined)
  })

  test('renders cron, timezone, and blackout fields', () => {
    render(<ScanScheduleForm onSubmit={mockOnSubmit} />)

    expect(screen.getByText('Configure Recurring Scan')).toBeInTheDocument()
    expect(screen.getByLabelText(/Cron Expression/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Timezone/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Start/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/End/i)).toBeInTheDocument()
  })

  test('submits a valid cron schedule payload', async () => {
    const user = userEvent.setup()
    render(<ScanScheduleForm onSubmit={mockOnSubmit} />)

    const cronInput = screen.getByDisplayValue('0 2 * * *')
    await user.clear(cronInput)
    await user.type(cronInput, '0 12 * * *')
    await user.selectOptions(screen.getByDisplayValue('UTC'), 'Asia/Kolkata')
    await user.click(screen.getByRole('button', { name: /Save Schedule/i }))

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        cron_expression: '0 12 * * *',
        timezone: 'Asia/Kolkata',
        blackout_start: null,
        blackout_end: null,
      })
    })
  })

  test('rejects invalid cron expressions', async () => {
    const user = userEvent.setup()
    render(<ScanScheduleForm onSubmit={mockOnSubmit} />)

    const cronInput = screen.getByDisplayValue('0 2 * * *')
    await user.clear(cronInput)
    await user.type(cronInput, '0 2')
    await user.click(screen.getByRole('button', { name: /Save Schedule/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/exactly 5 fields/i)
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  test('requires both blackout times when one is provided', async () => {
    const user = userEvent.setup()
    render(<ScanScheduleForm onSubmit={mockOnSubmit} />)

    fireEvent.change(screen.getByLabelText(/Start/i), { target: { value: '22:00' } })
    await user.click(screen.getByRole('button', { name: /Save Schedule/i }))

    expect(screen.getByRole('alert')).toHaveTextContent(/Both start and end times/i)
    expect(mockOnSubmit).not.toHaveBeenCalled()
  })

  test('calls onCancel when provided', async () => {
    const user = userEvent.setup()
    render(<ScanScheduleForm onSubmit={mockOnSubmit} onCancel={mockOnCancel} />)

    await user.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(mockOnCancel).toHaveBeenCalled()
  })

  test('embedded mode keeps values after submit', async () => {
    const user = userEvent.setup()
    render(<ScanScheduleForm embedded onSubmit={mockOnSubmit} submitLabel="Create Workflow" />)

    const cronInput = screen.getByDisplayValue('0 2 * * *')
    await user.clear(cronInput)
    await user.type(cronInput, '0 12 * * *')
    await user.click(screen.getByRole('button', { name: /Create Workflow/i }))

    await waitFor(() => expect(mockOnSubmit).toHaveBeenCalled())
    expect(cronInput).toHaveDisplayValue('0 12 * * *')
  })
})
