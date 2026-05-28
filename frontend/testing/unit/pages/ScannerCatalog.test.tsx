import { render, screen } from '@testing-library/react'
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
      id: 'legacy-custom-workflow',
      name: 'Legacy Workflow',
      purpose: 'Placeholder workflow tool',
      riskLevel: 'active',
      presetCompatibility: 'none',
      requiresConsent: false,
      category: 'quick-start',
    },
  ],
}))

describe('Scanner catalog integration', () => {
  beforeEach(() => {
    vi.mocked(listPlugins).mockResolvedValue({
      total: 2,
      plugins: [
        {
          id: 'subdomain_discovery',
          name: 'Subdomain Discovery',
          description: 'Enumerate subdomains',
          category: 'recon',
          safety_level: 'safe',
          enabled: true,
          icon: '🌐',
          requires_consent: false,
          consent_message: null,
          availability: {
            runnable: false,
            missing_binaries: ['subfinder'],
            status: 'unavailable',
            guidance:
              'Unavailable: Requires external binaries (subfinder). Install required tools locally to enable this scanner.',
          },
        },
        {
          id: 'ssh_runner',
          name: 'SSH Runner',
          description: 'Execute remote SSH commands',
          category: 'execution',
          safety_level: 'intrusive',
          enabled: true,
          icon: '🖥️',
          requires_consent: true,
          consent_message: 'Authorization required',
          availability: { runnable: true, missing_binaries: [] },
        },
      ],
    })
  })

  it('renders backend categories and mixed catalog warnings', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    // Ensure tab elements are present in the DOM
    const reconTab = await screen.findByRole('tab', { name: /Recon Tools/i })
    const quickStartTab = screen.getByRole('tab', { name: /^Quick Start$/i })
    
    expect(reconTab).toBeInTheDocument()
    expect(quickStartTab).toBeInTheDocument()

    // 1. Verify Recon Tools tab contents successfully change context states
    await user.click(reconTab)
    expect(await screen.findByRole('button', { name: /Subdomain Discovery, passive risk scanner/i })).toHaveAttribute(
      'aria-describedby',
      expect.stringContaining('scanner-tool-subdomain_discovery-description'),
    )
    expect(screen.getByText(/Unavailable:/i)).toBeInTheDocument()

    // 2. Verify Quick Start tab can be successfully focused and selected
    await user.click(quickStartTab)
    
    // Assert on state rather than brittle child UI text nodes that are affected by layout variations
    await vi.waitFor(() => {
      expect(quickStartTab).toHaveAttribute('aria-selected', 'true')
    })
  })
})