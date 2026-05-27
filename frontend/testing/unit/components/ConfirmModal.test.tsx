import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import ConfirmModal from '../../../src/components/ConfirmModal'

describe('ConfirmModal', () => {
  const defaultProps = {
    isOpen: true,
    title: 'Delete_Record',
    message: 'Are you sure you want to delete this record?',
    confirmLabel: 'Delete',
    danger: true,
    onConfirm: vi.fn(),
    onCancel: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal when isOpen is true', () => {
    render(<ConfirmModal {...defaultProps} />)
    expect(screen.getByText('Delete_Record')).toBeInTheDocument()
    expect(screen.getByText('Are you sure you want to delete this record?')).toBeInTheDocument()
  })

  it('does not render modal when isOpen is false', () => {
    render(<ConfirmModal {...defaultProps} isOpen={false} />)
    expect(screen.queryByText('Delete_Record')).not.toBeInTheDocument()
  })

  it('calls onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /Delete/i }))
    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(defaultProps.onCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onCancel when backdrop is clicked', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.click(document.querySelector('.fixed.inset-0')!)
    expect(defaultProps.onCancel).toHaveBeenCalled()
  })

  it('calls onCancel when Escape key is pressed', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.keyboard('{Escape}')
    expect(defaultProps.onCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onConfirm when Enter key is pressed', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.keyboard('{Enter}')
    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1)
  })

  it('does not call onConfirm when cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<ConfirmModal {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(defaultProps.onConfirm).not.toHaveBeenCalled()
  })
})
