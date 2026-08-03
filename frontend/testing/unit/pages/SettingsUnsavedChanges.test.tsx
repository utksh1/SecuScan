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
  return render(
    <ThemeProvider>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </ThemeProvider>,
  )
}

describe('Settings — unsaved changes warning', () => {
  beforeEach(() => {
    localStorage.removeItem('secuscan-config')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })

  it('shows no unsaved-changes indicator on initial load', () => {
    renderSettings()

    expect(screen.queryByText(/unsaved_changes_pending/i)).not.toBeInTheDocument()
  })

  it('shows the unsaved-changes indicator after editing a field', async () => {
    const user = userEvent.setup()
    renderSettings()

    const themeSelect = screen.getByRole('combobox', { name: /visual spectrum theme/i })
    await user.selectOptions(themeSelect, 'light')

    expect(screen.getByText(/unsaved_changes_pending/i)).toBeInTheDocument()
  })

  it('clears the unsaved-changes indicator after saving', async () => {
    const user = userEvent.setup()
    renderSettings()

    const themeSelect = screen.getByRole('combobox', { name: /visual spectrum theme/i })
    await user.selectOptions(themeSelect, 'light')
    expect(screen.getByText(/unsaved_changes_pending/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /COMMIT_ENGINE_CHANGES/i }))

    expect(screen.queryByText(/unsaved_changes_pending/i)).not.toBeInTheDocument()
  })

  it('warns before unload when there are unsaved changes', async () => {
    const user = userEvent.setup()
    renderSettings()

    const themeSelect = screen.getByRole('combobox', { name: /visual spectrum theme/i })
    await user.selectOptions(themeSelect, 'light')

    const event = new Event('beforeunload', { cancelable: true })
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
    window.dispatchEvent(event)

    expect(preventDefaultSpy).toHaveBeenCalled()
  })

  it('does not warn before unload when there are no unsaved changes', () => {
    renderSettings()

    const event = new Event('beforeunload', { cancelable: true })
    const preventDefaultSpy = vi.spyOn(event, 'preventDefault')
    window.dispatchEvent(event)

    expect(preventDefaultSpy).not.toHaveBeenCalled()
  })

  it('clears the unsaved-changes indicator after a factory reset', async () => {
    const user = userEvent.setup()
    renderSettings()

    const themeSelect = screen.getByRole('combobox', { name: /visual spectrum theme/i })
    await user.selectOptions(themeSelect, 'light')
    expect(screen.getByText(/unsaved_changes_pending/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /ENGINE_RESET/i }))
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(screen.queryByText(/unsaved_changes_pending/i)).not.toBeInTheDocument()
  })
})