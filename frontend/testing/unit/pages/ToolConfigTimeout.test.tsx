import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ToolConfig from '../../../src/pages/ToolConfig'
import { getPluginSchema, listPlugins, startTask, getSettings, listTargetPolicies, listCredentialProfiles, listSessionProfiles } from '../../../src/api'
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
}))

describe('ToolConfig timeout control', () => {
  beforeEach(() => {
    addToast.mockReset()
    vi.mocked(listPlugins).mockResolvedValue({
      total: 1,
      plugins: [
        {
          id: 'nikto',
          name: 'Nikto',
          description: 'Web scanner',
          category: 'web',
          safety_level: 'intrusive',
          enabled: true,
          icon: '🔧',
          requires_consent: true,
          consent_message: 'Auth required',
          availability: { runnable: false, missing_binaries: ['nikto'] },
        },
      ],
    })

    vi.mocked(getPluginSchema).mockResolvedValue({
      id: 'nikto',
      name: 'Nikto',
      description: 'Web scanner',
      fields: [
        { id: 'target', label: 'Target', type: 'string', required: true, placeholder: 'example.com' },
        {
          id: 'max_scan_time',
          label: 'Max Scan Time (seconds)',
          type: 'integer',
          required: false,
          default: 600,
          validation: { min: 30, max: 7200 },
        },
      ],
      presets: {},
      safety: { level: 'intrusive', requires_consent: true },
    })

    vi.mocked(getSettings).mockResolvedValue({ sandbox: { default_timeout: 600 } })
    vi.mocked(listTargetPolicies).mockResolvedValue({ total: 0, items: [] })
    vi.mocked(listCredentialProfiles).mockResolvedValue({ total: 0, items: [] })
    vi.mocked(listSessionProfiles).mockResolvedValue({ total: 0, items: [] })
    vi.mocked(startTask).mockResolvedValue({ task_id: 'task-1', status: 'queued', created_at: 'now', stream_url: '' })
    vi.mocked(listTargetPolicies).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(listCredentialProfiles).mockResolvedValue({ items: [], total: 0 })
    vi.mocked(listSessionProfiles).mockResolvedValue({ items: [], total: 0 })
  })

  it('renders integer input with constrained min/max', async () => {
    render(
      <MemoryRouter initialEntries={['/toolkit/nikto']}>
        <Routes>
          <Route path={routes.scanTool} element={<ToolConfig />} />
        </Routes>
      </MemoryRouter>,
    )

    const input = await screen.findByLabelText(/Max Scan Time/i)
    // min from field.validation
    expect(input).toHaveAttribute('min', '30')
    // max is min(field.validation.max, server default_timeout)
    expect(input).toHaveAttribute('max', '600')
  })
})
