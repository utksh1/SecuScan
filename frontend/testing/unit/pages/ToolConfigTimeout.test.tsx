import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ToolConfig from '../../../src/pages/ToolConfig'
import { getPluginSchema, listPlugins, startTask, getSettings } from '../../../src/api'
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
  listTargetPolicies: vi.fn().mockResolvedValue([]),
  listCredentialProfiles: vi.fn().mockResolvedValue([]),
  listSessionProfiles: vi.fn().mockResolvedValue([]),
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
    vi.mocked(startTask).mockResolvedValue({ task_id: 'task-1', status: 'queued', created_at: 'now', stream_url: '' })
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
    // max is min(field.validation.max, server default_timeout), wait for serverLimits
    await waitFor(() => {
      expect(input).toHaveAttribute('max', '600')
    })
  })
})
