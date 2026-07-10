import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock only the network boundary; the component's own error-handling logic
// under test is real.
vi.mock('../../../src/api', () => ({
  authenticateWithApiKey: vi.fn(),
}))

import ApiKeySetupScreen from '../../../src/components/ApiKeySetupScreen'
import { authenticateWithApiKey } from '../../../src/api'

describe('ApiKeySetupScreen — error handling (issue #1412)', () => {
  beforeEach(() => {
    vi.mocked(authenticateWithApiKey).mockReset()
  })

  it('renders error feedback when a failed API-key setup is mocked', async () => {
    const user = userEvent.setup()
    vi.mocked(authenticateWithApiKey).mockRejectedValueOnce(
      new Error('Invalid API key'),
    )
    const onSaved = vi.fn()

    render(<ApiKeySetupScreen onSaved={onSaved} />)

    await user.type(screen.getByLabelText('Backend API Key'), 'wrong-key')
    await user.click(screen.getByRole('button', { name: 'Save and connect' }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Invalid API key')
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('allows retrying/editing the key after a failed attempt', async () => {
    const user = userEvent.setup()
    vi.mocked(authenticateWithApiKey)
      .mockRejectedValueOnce(new Error('Invalid API key'))
      .mockResolvedValueOnce(undefined)
    const onSaved = vi.fn()

    render(<ApiKeySetupScreen onSaved={onSaved} />)

    const input = screen.getByLabelText('Backend API Key') as HTMLInputElement
    const saveButton = screen.getByRole('button', { name: 'Save and connect' })

    // First attempt fails.
    await user.type(input, 'wrong-key')
    await user.click(saveButton)
    await screen.findByRole('alert')

    // The field must still be editable after the failure.
    expect(input).not.toBeDisabled()

    // Correct the key and retry.
    await user.clear(input)
    await user.type(input, 'correct-key')
    await user.click(saveButton)

    await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(authenticateWithApiKey).toHaveBeenCalledTimes(2)
    expect(authenticateWithApiKey).toHaveBeenLastCalledWith('correct-key')
  })
})