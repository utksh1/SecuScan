import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scanner from '../Scanner'
import { listPlugins } from '../../api'

vi.mock('../../api', () => ({
  listPlugins: vi.fn(),
}))

vi.mock('../../data/scanTools', () => ({
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

describe('Scanner empty-state UX', () => {
  beforeEach(() => {
    vi.mocked(listPlugins).mockResolvedValue({
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
  })

  it('shows search-zero and category-zero guidance', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    await screen.findByText(/WHOIS Lookup/i)
    await user.type(screen.getByPlaceholderText('SEARCH_PROTOCOLS...'), 'nothing-will-match')
    expect(screen.getByText(/No tools match search/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Clear Search/i }))
    expect(screen.queryByText(/No tools match search/i)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Robots/i }))
    await waitFor(() => {
      expect(screen.getByText(/No tools available in this category/i)).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /Go to Quick Start/i }))
    await waitFor(() => {
      expect(screen.queryByText(/No tools available in this category/i)).not.toBeInTheDocument()
    })
  })
})
