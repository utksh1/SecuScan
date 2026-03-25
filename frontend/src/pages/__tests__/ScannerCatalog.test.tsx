import { render, screen } from '@testing-library/react'
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
          availability: { runnable: false, missing_binaries: ['subfinder'] },
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

    expect(await screen.findByRole('button', { name: /Recon Tools/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /^Quick Start$/i })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Recon Tools/i }))
    await screen.findByText(/Subdomain Discovery/i)
    expect(screen.getByText(/Missing: subfinder/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^Quick Start$/i }))
    expect(await screen.findByText(/Backend plugin pending/i)).toBeInTheDocument()
  })
})
