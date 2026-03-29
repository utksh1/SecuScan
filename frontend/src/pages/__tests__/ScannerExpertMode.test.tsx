import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scanner from '../Toolkit'
import { listPlugins } from '../../api'

vi.mock('../../api', () => ({
  listPlugins: vi.fn(),
}))

vi.mock('../../data/scanTools', () => ({
  scanTools: [],
}))

describe('Scanner tool visibility', () => {
  beforeEach(() => {
    vi.mocked(listPlugins).mockResolvedValue({
      total: 2,
      plugins: [
        {
          id: 'metasploit',
          name: 'Metasploit',
          description: 'Exploit connector',
          category: 'expert',
          safety_level: 'exploit',
          enabled: true,
          icon: '🚀',
          requires_consent: true,
          consent_message: 'Authorized usage only',
          availability: { runnable: true, missing_binaries: [] },
        },
        {
          id: 'subdomain_discovery',
          name: 'Subdomain Discovery',
          description: 'Recon discovery',
          category: 'recon',
          safety_level: 'safe',
          enabled: true,
          icon: '🌐',
          requires_consent: false,
          consent_message: null,
          availability: { runnable: true, missing_binaries: [] },
        },
      ],
    })
  })

  it('shows expert tools by default with no expert mode toggle', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('button', { name: /Recon Tools/i }))
    await screen.findByText(/Subdomain Discovery/i)

    await user.click(screen.getByRole('button', { name: /Exploit Detection/i }))
    expect(await screen.findByText(/Metasploit/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Expert Mode/i })).not.toBeInTheDocument()
  })
})
