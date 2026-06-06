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

describe('Settings theme wiring', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-theme')
    document.documentElement.classList.remove('theme-light')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })

  it('applies selected theme globally and persists it', async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>,
    )

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
})
