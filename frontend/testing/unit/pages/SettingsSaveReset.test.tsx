import { render, screen, fireEvent } from '@testing-library/react'
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
})
