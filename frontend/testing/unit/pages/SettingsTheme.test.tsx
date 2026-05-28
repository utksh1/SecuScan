import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'
import { vi } from 'vitest'

vi.mock('../../../src/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../../src/api')>()
  return {
    ...actual,
    getWebhooks: vi.fn().mockResolvedValue({ slack_url: '', discord_url: '', custom_url: '' }),
    updateWebhooks: vi.fn().mockResolvedValue({ slack_url: '', discord_url: '', custom_url: '' }),
  }
})

describe('Settings theme wiring', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-theme')
    document.documentElement.classList.remove('theme-light')
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

    const themeSelect = screen.getAllByRole('combobox')[3]
    await user.selectOptions(themeSelect, 'light')
    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))

    expect(document.documentElement.classList.contains('theme-light')).toBe(true)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('light')

    await user.selectOptions(screen.getAllByRole('combobox')[3], 'dark')
    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))

    expect(document.documentElement.classList.contains('theme-light')).toBe(false)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('dark')
  })
})
