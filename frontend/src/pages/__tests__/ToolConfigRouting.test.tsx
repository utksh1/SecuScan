import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ToolConfig from '../ToolConfig'
import { routes } from '../../routes'
import { getPluginSchema, listPlugins } from '../../api'

const mockNavigate = vi.fn()

vi.mock('../../components/ToastContext', () => ({
  useToast: () => ({ addToast: vi.fn() }),
}))

vi.mock('../../api', () => ({
  listPlugins: vi.fn(),
  getPluginSchema: vi.fn(),
  startTask: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

describe('ToolConfig route consistency', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
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
    vi.mocked(getPluginSchema).mockResolvedValue({
      id: 'whois_lookup',
      name: 'WHOIS Lookup',
      description: 'Domain registration information',
      fields: [{ id: 'target', label: 'Domain', type: 'string', required: true }],
      presets: { default: {} },
      safety: { level: 'safe', requires_consent: false },
    })
  })

  it('redirects unknown tool ids to /scans', async () => {
    render(
      <MemoryRouter initialEntries={['/scans/unknown-tool']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith(routes.scans)
    })
  })

  it('uses /scans for the back button destination', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/scans/whois_lookup']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    const backIcon = await screen.findByText('arrow_back')
    const backButton = backIcon.closest('button')
    expect(backButton).not.toBeNull()

    await user.click(backButton as HTMLButtonElement)
    expect(mockNavigate).toHaveBeenCalledWith(routes.scans)
  })
})
