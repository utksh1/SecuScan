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
