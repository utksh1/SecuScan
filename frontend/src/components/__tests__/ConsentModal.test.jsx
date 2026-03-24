import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ConsentModal from '../ConsentModal'

describe('ConsentModal', () => {
  const mockPlugin = {
    name: 'Test Plugin',
    description: 'A plugin for testing',
    safety: {
      level: 'safe',
      requires_consent: true,
      description: 'Is totally safe'
    }
  }

  it('does not render if plugin is null', () => {
    const { container } = render(
      <ConsentModal plugin={null} onConfirm={() => {}} onCancel={() => {}} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders plugin details correctly', () => {
    render(
      <ConsentModal plugin={mockPlugin} onConfirm={() => {}} onCancel={() => {}} />
    )

    expect(screen.getByText('Consent Required')).toBeInTheDocument()
    expect(screen.getByText('Test Plugin')).toBeInTheDocument()
    expect(screen.getByText(/A plugin for testing/i)).toBeInTheDocument()
  })

  it('calls onCancel when Cancel button is clicked', async () => {
    const handleCancel = vi.fn()
    render(
      <ConsentModal plugin={mockPlugin} onConfirm={() => {}} onCancel={handleCancel} />
    )

    fireEvent.click(screen.getByText('Cancel'))
    expect(handleCancel).toHaveBeenCalledTimes(1)
  })

  it('calls onConfirm when Proceed button is clicked', async () => {
    const handleConfirm = vi.fn()
    render(
      <ConsentModal plugin={mockPlugin} onConfirm={handleConfirm} onCancel={() => {}} />
    )

    fireEvent.click(screen.getByText('I Understand, Proceed'))
    expect(handleConfirm).toHaveBeenCalledTimes(1)
  })
})
