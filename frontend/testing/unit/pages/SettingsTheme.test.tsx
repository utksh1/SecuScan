import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'
import { listNotificationRules } from '../../../src/api'

vi.mock('../../../src/api', async () => {
  const actual: any = await vi.importActual('../../../src/api')
  return {
    ...actual,
    listNotificationRules: vi.fn(),
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

describe('Settings theme wiring', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-theme')
    document.documentElement.classList.remove('theme-light')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })

  it('applies selected theme globally and persists it', async () => {
    const user = userEvent.setup()
    renderSettings()

    const themeSelect = screen.getByRole('combobox', { name: /visual spectrum theme/i })

    await user.selectOptions(themeSelect, 'light')
    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))
    expect(document.documentElement.classList.contains('theme-light')).toBe(true)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('light')

    await user.selectOptions(themeSelect, 'dark')
    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))
    expect(document.documentElement.classList.contains('theme-light')).toBe(false)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('dark')
  })

  it('opens reset confirmation modal when ENGINE_RESET is clicked', async () => {
    const user = userEvent.setup()
    renderSettings()

    await user.click(screen.getByRole('button', { name: /ENGINE_RESET/i }))

    expect(
      screen.getByText(/Restore engine to factory specifications/i),
    ).toBeInTheDocument()
  })
})
