import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ToolConfig from '../../../src/pages/ToolConfig'
import { getPluginSchema, listPlugins, startTask, getSettings, listTargetPolicies, listCredentialProfiles, listSessionProfiles, previewCommand } from '../../../src/api'
import { routes } from '../../../src/routes'

const addToast = vi.fn()

vi.mock('../../../src/components/ToastContext', () => ({
  useToast: () => ({ addToast }),
}))

vi.mock('../../../src/api', () => ({
  listPlugins: vi.fn(),
  getPluginSchema: vi.fn(),
  startTask: vi.fn(),
  getSettings: vi.fn(),
  listTargetPolicies: vi.fn(),
  listCredentialProfiles: vi.fn(),
  listSessionProfiles: vi.fn(),
  previewCommand: vi.fn(),
}))

describe('ToolConfig dynamic schema flow', () => {
  beforeEach(() => {
    vi.mocked(previewCommand).mockResolvedValue({ command: ['subfinder', '-d', 'example.com'] })
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
          availability: {
            runnable: false,
            missing_binaries: ['subfinder'],
            status: 'unavailable',
            guidance:
              'Unavailable: Requires external binaries (subfinder). Install required tools locally to enable this scanner.',
          },
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
    vi.mocked(getSettings).mockResolvedValue(null)
    vi.mocked(listTargetPolicies).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(listCredentialProfiles).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(listSessionProfiles).mockResolvedValue({ items: [], total: 0 })
  })

  it('renders dynamic fields and submits startTask with consent', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/toolkit/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText(/Subdomain Discovery/i)
    expect(
      screen.getByText(/Install required tools locally/i)
    ).toBeInTheDocument()
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
        expect.any(Object),
      )
    })
  })
  it('falls back gracefully when guidance is absent', async () => {
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
          requires_consent: false,
          consent_message: null,
          availability: {
            runnable: false,
            missing_binaries: ['subfinder'],
          },
        },
      ],
    })

    render(
      <MemoryRouter initialEntries={['/toolkit/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText(/Subdomain Discovery/i)

    expect(
      screen.getByText(/subfinder|Install required tools locally|Unavailable:/i)
    ).toBeInTheDocument()
  })

  it('validates dynamic fields in real-time and disables scan button', async () => {
    vi.mocked(listPlugins).mockResolvedValue({
      total: 1,
      plugins: [
        {
          id: 'nuclei_mock',
          name: 'Nuclei Mock',
          description: 'Mock scanner',
          category: 'web',
          safety_level: 'intrusive',
          enabled: true,
          icon: '🔧',
          requires_consent: false,
          availability: {
            runnable: true,
            missing_binaries: [],
          },
        },
      ],
    })

    vi.mocked(getPluginSchema).mockResolvedValue({
      id: 'nuclei_mock',
      name: 'Nuclei Mock',
      description: 'Mock scanner',
      fields: [
        {
          id: 'target',
          label: 'Target',
          type: 'string',
          required: true,
          placeholder: 'https://secuscan.in',
          validation: {
            pattern: '^https?://',
            message: 'Must be a valid URL',
          },
        },
      ],
      presets: {},
      safety: { level: 'intrusive', requires_consent: false },
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/toolkit/nuclei_mock']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByText(/Nuclei Mock/i)
    const targetInput = screen.getByPlaceholderText('https://secuscan.in')

    // Initially FIX_PARAMETERS because target is required and empty
    expect(screen.getByRole('button', { name: /INITIATE_SCAN/i })).toHaveAttribute('aria-disabled', 'true')
    expect(screen.getByText(/1 field.*attention/i)).toBeInTheDocument()

    // Type invalid data
    await user.type(targetInput, 'not-a-url')
    expect(screen.getByText(/Must be a valid URL/i)).toBeInTheDocument()
    expect(targetInput).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText(/1 field.*attention/i)).toBeInTheDocument()

    // Clear and type valid data
    await user.clear(targetInput)
    await user.type(targetInput, 'https://example.com')
    expect(screen.queryByText(/Must be a valid URL/i)).not.toBeInTheDocument()
    expect(targetInput).toHaveAttribute('aria-invalid', 'false')
    expect(screen.getByRole('button', { name: /INITIATE_SCAN/i })).toHaveAttribute('aria-disabled', 'false')
  })

  it('focuses the first invalid field when scan start is attempted', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/toolkit/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    const targetInput = await screen.findByPlaceholderText('example.com')
    await user.click(screen.getByRole('checkbox', { name: /I have explicit authorization/i }))
    await user.click(screen.getByRole('button', { name: /INITIATE_SCAN/i }))

    expect(targetInput).toHaveFocus()
    expect(addToast).toHaveBeenCalledWith(
      'Fix highlighted scan parameters before starting the scan.',
      'error',
    )
  })

  it('keeps help and error descriptions wired together for invalid fields', async () => {
    vi.mocked(listPlugins).mockResolvedValue({
      total: 1,
      plugins: [
        {
          id: 'url_guard',
          name: 'URL Guard',
          description: 'URL validation',
          category: 'web',
          safety_level: 'safe',
          enabled: true,
          icon: '🔗',
          requires_consent: false,
          availability: {
            runnable: true,
            missing_binaries: [],
          },
        },
      ],
    })

    vi.mocked(getPluginSchema).mockResolvedValue({
      id: 'url_guard',
      name: 'URL Guard',
      description: 'URL validation',
      fields: [
        {
          id: 'target',
          label: 'Target',
          type: 'string',
          required: true,
          placeholder: 'https://secuscan.in',
          help: 'Enter a fully qualified URL.',
          validation: {
            pattern: '^https?://',
            message: 'Must be a valid URL',
          },
        },
      ],
      presets: {},
      safety: { level: 'safe', requires_consent: false },
    })

    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/toolkit/url_guard']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    const targetInput = await screen.findByPlaceholderText('https://secuscan.in')
    await user.type(targetInput, 'bad-url')

    expect(screen.getByText('Enter a fully qualified URL.')).toBeInTheDocument()
    expect(screen.getByText('Must be a valid URL')).toBeInTheDocument()
    expect(targetInput).toHaveAttribute('aria-describedby', 'help-target error-target')
  })

  it('renders command preview and updates on input changes', async () => {
    const user = userEvent.setup()
    vi.mocked(previewCommand).mockResolvedValue({
      command: ['subfinder', '-d', 'example.com'],
    })

    render(
      <MemoryRouter initialEntries={['/toolkit/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    const targetInput = await screen.findByPlaceholderText('example.com')
    await user.type(targetInput, 'example.com')

    await waitFor(() => {
      expect(previewCommand).toHaveBeenCalledWith(
        'subdomain_discovery',
        expect.objectContaining({ target: 'example.com' }),
      )
    })

    expect(await screen.findByText('subfinder -d example.com')).toBeInTheDocument()
    expect(screen.getByText(/Note: This preview is generated locally\/sanitized/i)).toBeInTheDocument()
  })

  it('shows validation error warning in preview panel if inputs are invalid', async () => {
    render(
      <MemoryRouter initialEntries={['/toolkit/subdomain_discovery']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    await screen.findByPlaceholderText('example.com')
    expect(await screen.findByText(/Fix highlighted validation errors to preview command./i)).toBeInTheDocument()
  })
})
