import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import ApiKeySetupModal from '../../../src/components/ApiKeySetupModal'

vi.mock('../../../src/api', () => ({
  authenticateWithApiKey: vi.fn(),
}))

import { authenticateWithApiKey } from '../../../src/api'

describe('ApiKeySetupModal Error Handling', () => {
  const defaultProps = {
    onSaved: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows standard validation error on empty submission', async () => {
    const user = userEvent.setup()
    render(<ApiKeySetupModal {...defaultProps} />)

    await user.click(screen.getByRole('button', { name: /save and connect/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Please enter the API key.')
    expect(authenticateWithApiKey).not.toHaveBeenCalled()
  })

  it('shows backend error message when api key is rejected', async () => {
    const user = userEvent.setup()
    const backendErrorMsg = 'Invalid/Expired API token'
    vi.mocked(authenticateWithApiKey).mockRejectedValue(new Error(backendErrorMsg))

    render(<ApiKeySetupModal {...defaultProps} />)

    const input = screen.getByLabelText('Backend API Key')
    await user.type(input, 'bad-key')
    await user.click(screen.getByRole('button', { name: /save and connect/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(backendErrorMsg)
    expect(defaultProps.onSaved).not.toHaveBeenCalled()
  })

  it('ensures sensitive key text is not echoed in failure UI', async () => {
    const user = userEvent.setup()
    const sensitiveKey = 'SUPER_SECRET_TOKEN_999'
    vi.mocked(authenticateWithApiKey).mockRejectedValue(new Error('Authentication failed. Check the API key.'))

    render(<ApiKeySetupModal {...defaultProps} />)

    const input = screen.getByLabelText('Backend API Key')
    await user.type(input, sensitiveKey)
    await user.click(screen.getByRole('button', { name: /save and connect/i }))

    // Assert useful error message is visible
    const alert = await screen.findByRole('alert')
    expect(alert).toBeInTheDocument()

    // Assert sensitive key text is NOT in the error message / failure UI text content
    expect(alert.textContent).not.toContain(sensitiveKey)
  })
})
