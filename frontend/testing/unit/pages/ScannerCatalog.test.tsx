import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Toolkit from '../../../src/pages/Toolkit'  // ✅ FIXED: was Scanner
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
      isQuickStart: true,  // ✅ ADDED: required for quick-start category
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
        <Toolkit />  {/* ✅ FIXED: was Scanner */}
      </MemoryRouter>,
    )

    const reconTab = await screen.findByRole('tab', { name: /Recon Tools/i })
    const quickStartTab = screen.getByRole('tab', { name: /^Quick Start$/i })

    expect(reconTab).toBeInTheDocument()
    expect(quickStartTab).toBeInTheDocument()

    await user.click(reconTab)
    expect(await screen.findByRole('button', { name: /Subdomain Discovery, active risk scanner/i })).toHaveAttribute(
      'aria-describedby',
      expect.stringContaining('scanner-tool-subdomain_discovery-description'),
    )
    expect(screen.getByText(/Unavailable:/i)).toBeInTheDocument()

    await user.click(quickStartTab)
    await vi.waitFor(() => {
      expect(quickStartTab).toHaveAttribute('aria-selected', 'true')
    })
  })
})