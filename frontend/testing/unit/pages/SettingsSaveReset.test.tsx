import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'
const DEFAULT_CONFIG = {
  concurrentScans: 8,
  scanTimeout: 3600,
  scanIntensity: 'standard',
  dataRetention: 30,
  shodanKey: '',
  virustotalKey: '',
  ipWhitelist: '127.0.0.1\n10.0.0.0/8',
  autoPurgeFailed: false,
  autoRescanCritical: true,
  timezone: 'auto',
  theme: 'dark',
  notifications: {
    scanComplete: true,
    criticalFindings: true,
    systemAlerts: true,
  },
}
function renderSettings() {
  render(
    <ThemeProvider>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </ThemeProvider>,
  )
}
function getInputByLabelText(labelText: RegExp) {
  const label = screen.getByText(labelText)
  const card = label.closest('div')?.parentElement
  const input = card?.querySelector('input')
  if (!input) {
    throw new Error(`Could not find input for label: ${label.textContent ?? labelText}`)
  }
  return input as HTMLInputElement
}
describe('Settings save/reset behavior', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-config')
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })
  it('saves the current config to localStorage (secuscan-config)', async () => {
    const user = userEvent.setup()
    renderSettings()
    const concurrentOps = getInputByLabelText(/Concurrent_Operations/i)
    fireEvent.change(concurrentOps, { target: { value: '3' } })
    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))
    const savedRaw = window.localStorage.getItem('secuscan-config')
    expect(savedRaw).toBeTruthy()
    const saved = JSON.parse(savedRaw as string)
    expect(saved.concurrentScans).toBe(3)
  })
  it('resets config to defaults after confirmation and persists it', async () => {
    window.localStorage.setItem(
      'secuscan-config',
      JSON.stringify({ ...DEFAULT_CONFIG, concurrentScans: 2, shodanKey: 'abc' }),
    )
    const user = userEvent.setup()
    renderSettings()
    await user.click(screen.getByRole('button', { name: /ENGINE_RESET/i }))
    // Confirm via the new modal instead of window.confirm
    const confirmButton = await screen.findByRole('button', { name: /confirm/i })
    await user.click(confirmButton)
    const saved = JSON.parse(window.localStorage.getItem('secuscan-config') as string)
    expect(saved).toEqual(DEFAULT_CONFIG)
    const concurrentOps = getInputByLabelText(/Concurrent_Operations/i)
    expect(concurrentOps.value).toBe('8')
  })
  it('nuclear purge removes only secuscan-owned keys and preserves unrelated keys', async () => {
  const fetchSpy = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ status: 'logged_out' }),
  })
  vi.stubGlobal('fetch', fetchSpy)

  window.localStorage.setItem('secuscan-config', JSON.stringify(DEFAULT_CONFIG))
  window.localStorage.setItem('secuscan_api_key', 'test-api-key')
  window.localStorage.setItem('secuscan-saved-views', JSON.stringify([]))
  window.localStorage.setItem('secuscan-finding-review-state', JSON.stringify({}))
  window.localStorage.setItem('secuscan:preferred-export-format', 'html')
  window.localStorage.setItem('secuscan_recent_tools', JSON.stringify([]))
  window.localStorage.setItem('secuscan-theme', 'dark')
  window.localStorage.setItem('sidebar-expanded', 'true')
  // Set up an unrelated key
  window.localStorage.setItem('some-other-app-key', 'should-not-be-deleted')

  const user = userEvent.setup()
  renderSettings()

  await user.click(screen.getByRole('button', { name: /NUCLEAR_PURGE/i }))

  const confirmButton = await screen.findByRole('button', { name: /confirm/i })
  await user.click(confirmButton)

  // SecuScan keys should be gone
  expect(window.localStorage.getItem('secuscan-config')).toBeNull()
  expect(window.localStorage.getItem('secuscan_api_key')).toBeNull()
  expect(window.localStorage.getItem('secuscan-saved-views')).toBeNull()
  expect(window.localStorage.getItem('secuscan-finding-review-state')).toBeNull()
  expect(window.localStorage.getItem('secuscan:preferred-export-format')).toBeNull()
  expect(window.localStorage.getItem('secuscan_recent_tools')).toBeNull()
  expect(window.localStorage.getItem('secuscan-theme')).toBeNull()
  expect(window.localStorage.getItem('sidebar-expanded')).toBeNull()

  // Unrelated key should still be there
  expect(window.localStorage.getItem('some-other-app-key')).toBe('should-not-be-deleted')

  await waitFor(() => {
    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining('/auth/session/logout'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    )
  })
})
})
