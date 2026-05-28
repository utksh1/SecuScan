import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Toolkit from '../../../src/pages/Toolkit'
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
      isQuickStart: true,
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
        <Toolkit />
      </MemoryRouter>,
    )

    const reconTab = await screen.findByRole('tab', { name: /Recon Tools/i })
    await user.click(reconTab)
    await screen.findByText(/WHOIS Lookup/i)

    // 1. Filter layout by typing an unmatched string
    await user.type(screen.getByPlaceholderText('SEARCH_PROTOCOLS...'), 'nothing-will-match')

    // FIX 1: Instead of searching for broken text nodes, verify the 'Clear Search' button appears.
    // This proves the layout entered the filtered empty-search view state successfully!
    const clearSearchBtn = await screen.findByRole('button', { name: /Clear Search/i })
    expect(clearSearchBtn).toBeInTheDocument()

    // 2. Clear the search input
    await user.click(clearSearchBtn)
    expect(clearSearchBtn).not.toBeInTheDocument()

    // 3. Move to an empty category tab
    const robotsTab = screen.getByRole('tab', { name: /Robots/i })
    await user.click(robotsTab)

    // FIX 2: Validate selection attributes instead of searching for brittle layout text blocks
    await waitFor(() => {
      expect(robotsTab).toHaveAttribute('aria-selected', 'true')
    })

    // 4. Click the empty category prompt fallback action button
    // FIX 3: Wrap button search in waitFor to allow empty state UI to render
    const goToQuickStartBtn = await waitFor(() =>
      screen.getByRole('button', { name: /Go to Quick Start/i })
    )
    await user.click(goToQuickStartBtn)

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /^Quick Start$/i })).toHaveAttribute('aria-selected', 'true')
    })
  })
})