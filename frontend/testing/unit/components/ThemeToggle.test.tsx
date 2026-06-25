import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach } from 'vitest'
import ThemeToggle from '../../../src/components/ThemeToggle'
import { ThemeProvider } from '../../../src/components/ThemeContext'

const STORAGE_KEY = 'secuscan-theme'

function renderWithTheme() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  )
}

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorage.removeItem(STORAGE_KEY)
    document.documentElement.classList.remove('dark', 'theme-light')
  })

  it('renders a button with an accessible label', () => {
    renderWithTheme()
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label')
  })

  it('toggles from dark to light on click and persists to localStorage', async () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    const user = userEvent.setup()
    renderWithTheme()

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-pressed', 'true')

    await user.click(button)

    expect(localStorage.getItem(STORAGE_KEY)).toBe('light')
    expect(button).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles from light to dark on click and persists to localStorage', async () => {
    localStorage.setItem(STORAGE_KEY, 'light')
    const user = userEvent.setup()
    renderWithTheme()

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-pressed', 'false')

    await user.click(button)

    expect(localStorage.getItem(STORAGE_KEY)).toBe('dark')
    expect(button).toHaveAttribute('aria-pressed', 'true')
  })

  it('aria-label reflects the target theme, not the current one', () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    renderWithTheme()
    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-label', 'Toggle to light mode')
  })

  it('shows dark_mode icon when theme is light', () => {
    localStorage.setItem(STORAGE_KEY, 'light')
    renderWithTheme()
    expect(screen.getByText('dark_mode')).toBeTruthy()
  })

  it('shows light_mode icon when theme is dark', () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    renderWithTheme()
    expect(screen.getByText('light_mode')).toBeTruthy()
  })

  it('stops click propagation', async () => {
    localStorage.setItem(STORAGE_KEY, 'dark')
    const user = userEvent.setup()
    const parentHandler = vi.fn()
    render(
      <div onClick={parentHandler}>
        <ThemeProvider>
          <ThemeToggle />
        </ThemeProvider>
      </div>,
    )
    await user.click(screen.getByRole('button'))
    expect(parentHandler).not.toHaveBeenCalled()
  })

  it('applies sm size classes when size prop is sm', () => {
    render(
      <ThemeProvider>
        <ThemeToggle size="sm" />
      </ThemeProvider>,
    )
    const button = screen.getByRole('button')
    expect(button.className).toContain('w-9')
    expect(button.className).toContain('h-9')
  })
})
