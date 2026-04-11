import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import Settings from '../Settings'
import { ThemeProvider } from '../../components/ThemeContext'

describe('Settings theme wiring', () => {
  beforeEach(() => {
    window.localStorage.removeItem('secuscan-theme')
    document.documentElement.classList.remove('theme-light')
  })

  it('applies selected theme globally and persists it', async () => {
    const user = userEvent.setup()

    render(
      <ThemeProvider>
        <Settings />
      </ThemeProvider>,
    )

    await user.click(screen.getByRole('button', { name: /light/i }))
    expect(document.documentElement.classList.contains('theme-light')).toBe(true)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('light')

    await user.click(screen.getByRole('button', { name: /dark/i }))
    expect(document.documentElement.classList.contains('theme-light')).toBe(false)
    expect(window.localStorage.getItem('secuscan-theme')).toBe('dark')
  })
})
