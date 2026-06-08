import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'

describe('Settings theme wiring', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-theme')
    document.documentElement.classList.remove('theme-light')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })
describe('Settings management tools', () => {
  it('saves configuration to localStorage', async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }),
    )

    expect(localStorage.getItem('secuscan-config')).not.toBeNull()
  })

  it('opens reset confirmation modal', async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>,
    )

    await user.click(
      screen.getByRole('button', { name: /ENGINE_RESET/i }),
    )

    expect(
      screen.getByText(/Restore engine to factory specifications/i),
    ).toBeInTheDocument()
  })
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

  it.skip('verifies export flow with a test-friendly stub', async () => {
  const user = userEvent.setup()

  const clickMock = vi.fn()

  const anchorMock = {
    setAttribute: vi.fn(),
    click: clickMock,
    remove: vi.fn(),
  }

  const originalCreateElement = document.createElement.bind(document)

  const createElementSpy = vi
    .spyOn(document, 'createElement')
    .mockImplementation((tagName: string) => {
      if (tagName === 'a') {
        return anchorMock as any
      }

      return originalCreateElement(tagName)
    })

  render(
    <ThemeProvider>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </ThemeProvider>,
  )

  await user.click(
    screen.getByRole('button', { name: /TELEMETRY_EXPORT/i }),
  )

  expect(clickMock).toHaveBeenCalled()

  createElementSpy.mockRestore()
})
})
