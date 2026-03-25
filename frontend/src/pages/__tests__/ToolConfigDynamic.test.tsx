import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ToolConfig from '../ToolConfig'
import { getPluginSchema, listPlugins, startTask } from '../../api'
import { routes } from '../../routes'

const addToast = vi.fn()

vi.mock('../../components/ToastContext', () => ({
  useToast: () => ({ addToast }),
}))

vi.mock('../../api', () => ({
  listPlugins: vi.fn(),
  getPluginSchema: vi.fn(),
  startTask: vi.fn(),
}))

describe('ToolConfig dynamic schema flow', () => {
  beforeEach(() => {
    addToast.mockReset()
    vi.mocked(listPlugins).mockResolvedValue({
      total: 1,
      plugins: [
        {
          id: 'subdomain_discovery',
          name: 'Subdomain Discovery',
          description: 'Enumerate subdomains',
          category: 'recon',
          safety_level: 'safe',
          enabled: true,
          icon: '🌐',
          requires_consent: true,
          consent_message: 'Explicit authorization required',
          availability: { runnable: false, missing_binaries: ['subfinder'] },
        },
      ],
    })
    vi.mocked(getPluginSchema).mockResolvedValue({
      id: 'subdomain_discovery',
      name: 'Subdomain Discovery',
      description: 'Enumerate subdomains',
      fields: [
        { id: 'target', label: 'Domain', type: 'string', required: true, placeholder: 'example.com' },
        { id: 'threads', label: 'Threads', type: 'integer', required: false, default: 10 },
        {
          id: 'scan_type',
          label: 'Scan Type',
          type: 'select',
          required: false,
          default: 'passive',
          options: [
            { value: 'passive', label: 'Passive' },
            { value: 'active', label: 'Active' },
          ],
        },
      ],
      presets: {
        quick: { threads: 10, scan_type: 'passive' },
        comprehensive: { threads: 20, scan_type: 'active' },
      },
      safety: { level: 'safe', requires_consent: true },
    })
    vi.mocked(startTask).mockResolvedValue({
      task_id: 'task-123',
      status: 'queued',
      created_at: 'now',
      stream_url: '/api/v1/task/task-123/stream',
    })
  })

  it('renders dynamic fields and submits startTask with consent', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/scans/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText(/Subdomain Discovery/i)
    expect(screen.getByText(/Missing local binaries: subfinder/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('example.com')).toBeInTheDocument()
    expect(screen.getByDisplayValue('10')).toBeInTheDocument()
    await user.type(screen.getByPlaceholderText('example.com'), 'example.com')

    await user.click(screen.getByRole('button', { name: /INITIATE_SCAN/i }))
    expect(startTask).not.toHaveBeenCalled()

    await user.click(screen.getByRole('checkbox', { name: /I have explicit authorization/i }))
    await user.click(screen.getByRole('button', { name: /INITIATE_SCAN/i }))

    await waitFor(() => {
      expect(startTask).toHaveBeenCalledWith(
        'subdomain_discovery',
        expect.objectContaining({
          target: 'example.com',
        }),
        true,
        'quick',
      )
    })
  })
})
