import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ToastProvider, useToast } from '../../../src/components/ToastContext'

function ToastTrigger({ type = 'success' }: { type?: 'success' | 'error' }) {
  const { addToast } = useToast()

  return (
    <button type="button" onClick={() => addToast(`${type} message`, type)}>
      Show toast
    </button>
  )
}

describe('Toast accessibility', () => {
  it('announces non-critical notifications as status messages and provides a labelled dismiss control', async () => {
    const user = userEvent.setup()

    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    )

    await user.click(screen.getByRole('button', { name: /show toast/i }))

    expect(await screen.findByRole('status')).toHaveTextContent(/success message/i)

    await user.click(screen.getByRole('button', { name: /dismiss success notification/i }))

    await waitFor(() => {
      expect(screen.queryByText(/success message/i)).not.toBeInTheDocument()
    })
  })

  it('announces error notifications as alerts', async () => {
    const user = userEvent.setup()

    render(
      <ToastProvider>
        <ToastTrigger type="error" />
      </ToastProvider>,
    )

    await user.click(screen.getByRole('button', { name: /show toast/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/error message/i)
  })
})

describe('Toast deduplication', () => {
  it('collapses repeated identical notifications into a single toast with a count', async () => {
    const user = userEvent.setup()

    render(
      <ToastProvider>
        <ToastTrigger type="error" />
      </ToastProvider>,
    )

    const trigger = screen.getByRole('button', { name: /show toast/i })
    await user.click(trigger)
    await user.click(trigger)
    await user.click(trigger)

    const alerts = await screen.findAllByRole('alert')
    expect(alerts).toHaveLength(1)
    expect(alerts[0]).toHaveTextContent(/error message/i)
    expect(alerts[0]).toHaveTextContent('×3')
    expect(screen.getByLabelText(/repeated 3 times/i)).toBeInTheDocument()
  })

  it('keeps notifications with different message or type separate', async () => {
    const user = userEvent.setup()

    render(
      <ToastProvider>
        <ToastTrigger type="success" />
        <ToastTrigger type="error" />
      </ToastProvider>,
    )

    const [successTrigger, errorTrigger] = screen.getAllByRole('button', { name: /show toast/i })
    await user.click(successTrigger)
    await user.click(errorTrigger)

    expect(await screen.findByRole('status')).toHaveTextContent(/success message/i)
    expect(await screen.findByRole('alert')).toHaveTextContent(/error message/i)
    // Neither is collapsed, so no count badge appears.
    expect(screen.queryByText(/^×\d+$/)).not.toBeInTheDocument()
  })
})
