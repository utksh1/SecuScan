import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'
import {
  createNotificationRule,
  deleteNotificationRule,
  listNotificationRules,
  updateNotificationRule,
  listNotificationHistory,
  getScanWebhookSettings,
  setScanWebhookSettings,
  deleteScanWebhookSettings,
} from '../../../src/api'

vi.mock('../../../src/api', async () => {
  const actual: any = await vi.importActual('../../../src/api')
  return {
    ...actual,
    listNotificationRules: vi.fn(),
    createNotificationRule: vi.fn(),
    updateNotificationRule: vi.fn(),
    deleteNotificationRule: vi.fn(),
    listNotificationHistory: vi.fn(),
    getScanWebhookSettings: vi.fn(),
    setScanWebhookSettings: vi.fn(),
    deleteScanWebhookSettings: vi.fn(),
  }
})

function renderSettings() {
  render(
    <ThemeProvider>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </ThemeProvider>,
  )
}

describe('Settings notifications rules panel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.mocked(listNotificationRules).mockResolvedValue([
      {
        id: 'rule-1',
        name: 'Critical hook',
        severity_threshold: 'critical',
        channel_type: 'webhook',
        target_url_or_email: 'https://example.com/hook',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ] as any)
    vi.mocked(createNotificationRule).mockResolvedValue({} as any)
    vi.mocked(updateNotificationRule).mockResolvedValue({} as any)
    vi.mocked(deleteNotificationRule).mockResolvedValue({ rule_id: 'rule-1', deleted: true } as any)
    vi.mocked(listNotificationHistory).mockResolvedValue({ history: [], total: 0, limit: 10, offset: 0 } as any)
    vi.mocked(getScanWebhookSettings).mockResolvedValue({
      webhook_url: null,
      platform: null,
      configured: false,
      updated_at: null,
    } as any)
    vi.mocked(setScanWebhookSettings).mockResolvedValue({} as any)
    vi.mocked(deleteScanWebhookSettings).mockResolvedValue({ deleted: true } as any)
  })

  it('renders existing rules from API', async () => {
    renderSettings()
    expect(await screen.findByRole('heading', { name: /Notification_Rules/i })).toBeInTheDocument()
    expect(await screen.findByDisplayValue(/Critical hook/i)).toBeInTheDocument()
  })

  it('can create a rule', async () => {
    const user = userEvent.setup()
    renderSettings()

    await user.type(await screen.findByLabelText(/New rule name/i), 'High email')
    await user.type(screen.getByLabelText(/New rule target/i), 'alerts@example.com')
    await user.selectOptions(screen.getByLabelText(/New rule channel type/i), 'email')
    await user.selectOptions(screen.getByLabelText(/New rule severity threshold/i), 'high')

    await user.click(screen.getByRole('button', { name: /CREATE_RULE/i }))

    await waitFor(() => {
      expect(createNotificationRule).toHaveBeenCalled()
    })
    await waitFor(() => {
      expect(listNotificationRules).toHaveBeenCalled()
    })
  })

  it('can toggle active state', async () => {
    const user = userEvent.setup()
    renderSettings()
    const toggle = await screen.findByRole('button', { name: /Toggle rule rule-1/i })
    await user.click(toggle)
    await waitFor(() => {
      expect(updateNotificationRule).toHaveBeenCalledWith('rule-1', { is_active: false })
    })
  })
})

describe('Settings scan completion webhook panel', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.mocked(listNotificationRules).mockResolvedValue([])
    vi.mocked(createNotificationRule).mockResolvedValue({} as any)
    vi.mocked(updateNotificationRule).mockResolvedValue({} as any)
    vi.mocked(deleteNotificationRule).mockResolvedValue({ rule_id: 'rule-1', deleted: true } as any)
    vi.mocked(listNotificationHistory).mockResolvedValue({ history: [], total: 0, limit: 10, offset: 0 } as any)
    vi.mocked(getScanWebhookSettings).mockResolvedValue({
      webhook_url: null,
      platform: null,
      configured: false,
      updated_at: null,
    } as any)
    vi.mocked(setScanWebhookSettings).mockResolvedValue({
      webhook_url: 'https://hooks.slack.com/services/x',
      platform: 'slack',
      configured: true,
      updated_at: '2026-01-01T00:00:00Z',
    } as any)
    vi.mocked(deleteScanWebhookSettings).mockResolvedValue({ deleted: true } as any)
  })

  it('saves a new scan completion webhook URL', async () => {
    const user = userEvent.setup()
    renderSettings()

    const input = await screen.findByLabelText(/Scan completion webhook URL/i)
    await user.type(input, 'https://hooks.slack.com/services/x')
    await user.click(screen.getByRole('button', { name: /SAVE_WEBHOOK/i }))

    await waitFor(() => {
      expect(setScanWebhookSettings).toHaveBeenCalledWith('https://hooks.slack.com/services/x')
    })
    expect(await screen.findByText(/detected format: slack/i)).toBeInTheDocument()
  })
})
