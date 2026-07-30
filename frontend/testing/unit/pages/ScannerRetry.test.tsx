import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scanner from '../../../src/pages/Toolkit'
import { listPlugins } from '../../../src/api'

vi.mock('../../../src/api', () => ({
  listPlugins: vi.fn(),
}))

vi.mock('../../../src/data/scanTools', () => ({
  scanTools: [
    {
      id: 'legacy-quick-start',
      name: 'Legacy Quick Start',
      purpose: 'Legacy placeholder tool',
      riskLevel: 'passive',
      presetCompatibility: 'none',
      requiresConsent: false,
      category: 'quick-start',
    },
  ],
}))

describe('Scanner retry on plugin load failure', () => {
  it('shows retry action and recovers after retry succeeds', async () => {
    const user = userEvent.setup()

    vi.mocked(listPlugins)
      .mockRejectedValueOnce(new Error('catalog offline'))
      .mockResolvedValueOnce({
        total: 1,
        plugins: [
          {
            id: 'whois_lookup',
            name: 'WHOIS Lookup',
            description: 'Domain registration information',
            category: 'recon',
            safety_level: 'safe',
            enabled: true,
            icon: '🔎',
            requires_consent: false,
            consent_message: null,
            availability: { runnable: true, missing_binaries: [] },
          },
        ],
      })

    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/Catalog load failed/i)).toBeInTheDocument()
    expect(screen.getByText(/catalog offline/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Retry/i }))

    await waitFor(() => {
      expect(listPlugins).toHaveBeenCalledTimes(2)
    })

    await waitFor(() => {
      expect(screen.queryByText(/Catalog load failed/i)).not.toBeInTheDocument()
    })

    await user.click(screen.getByRole('tab', { name: /Recon Tools/i }))
    expect(await screen.findByText(/WHOIS Lookup/i)).toBeInTheDocument()
  })
})
