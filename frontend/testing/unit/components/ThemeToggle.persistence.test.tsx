import React from 'react'
import { render, screen, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import ThemeToggle from '../../../src/components/ThemeToggle'
import { ThemeProvider, useTheme } from '../../../src/components/ThemeContext'

const STORAGE_KEY = 'secuscan-theme'

/**
 * Regression coverage for theme persistence, reload, and reset-to-system flows.
 * Complements ThemeToggle.test.tsx (click/toggle behavior) with the gaps this
 * issue calls out: surviving a fresh mount (reload), reset-to-system, and
 * system-preference fallback when no manual override exists.
 */

function mockMatchMedia(prefersLight: boolean) {
  const listeners: Array<(e: MediaQueryListEvent) => void> = []
  const mql = {
    matches: prefersLight,
    media: '(prefers-color-scheme: light)',
    addEventListener: (_event: string, handler: (e: MediaQueryListEvent) => void) => {
      listeners.push(handler)
    },
    removeEventListener: (_event: string, handler: (e: MediaQueryListEvent) => void) => {
      const idx = listeners.indexOf(handler)
      if (idx !== -1) listeners.splice(idx, 1)
    },
  }

  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    ...mql,
    // The context queries 'prefers-color-scheme: light' for initial detection
    // and 'prefers-color-scheme: dark' for the change listener — both need to
    // resolve consistently from the same prefersLight flag.
    matches: query.includes('light') ? prefersLight : !prefersLight,
  }))

  return { listeners }
}

function renderToggle() {
  return render(
    <ThemeProvider>
      <ThemeToggle />
    </ThemeProvider>,
  )
}

// Small helper component to assert isSystemControlled from context directly
function SystemControlledProbe() {
  const { isSystemControlled } = useTheme()
  return <span data-testid="system-controlled">{String(isSystemControlled)}</span>
}

describe('Theme persistence regression', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark', 'theme-light')
    mockMatchMedia(false) // default: system prefers dark
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  describe('reload simulation (fresh mount reading existing localStorage)', () => {
    it('restores dark theme on fresh mount when localStorage has dark', () => {
      localStorage.setItem(STORAGE_KEY, 'dark')
      renderToggle()
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'true')
      expect(document.documentElement.classList.contains('dark')).toBe(true)
    })

    it('restores light theme on fresh mount when localStorage has light', () => {
      localStorage.setItem(STORAGE_KEY, 'light')
      renderToggle()
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'false')
      expect(document.documentElement.classList.contains('theme-light')).toBe(true)
    })

    it('survives toggle then simulated reload (unmount/remount) with the new value', async () => {
      localStorage.setItem(STORAGE_KEY, 'dark')
      const user = userEvent.setup()
      const { unmount } = renderToggle()

      await user.click(screen.getByRole('button'))
      expect(localStorage.getItem(STORAGE_KEY)).toBe('light')

      // Simulate a reload: unmount and mount a fresh provider tree
      unmount()
      renderToggle()

      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'false')
      expect(document.documentElement.classList.contains('theme-light')).toBe(true)
    })

    it('ignores invalid localStorage values and falls back to system preference', () => {
      localStorage.setItem(STORAGE_KEY, 'not-a-real-theme')
      mockMatchMedia(true) // system prefers light
      renderToggle()
      const button = screen.getByRole('button')
      expect(button).toHaveAttribute('aria-pressed', 'false')
    })
  })

  describe('system preference fallback (no manual override)', () => {
    it('uses system dark preference when localStorage is empty', () => {
      mockMatchMedia(false) // system prefers dark
      renderToggle()
      expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true')
    })

    it('uses system light preference when localStorage is empty', () => {
      mockMatchMedia(true) // system prefers light
      renderToggle()
      expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false')
    })

    it('reports isSystemControlled true when no manual override exists', () => {
      render(
        <ThemeProvider>
          <SystemControlledProbe />
        </ThemeProvider>,
      )
      expect(screen.getByTestId('system-controlled').textContent).toBe('true')
    })

    it('reports isSystemControlled false after a manual toggle', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider>
          <ThemeToggle />
          <SystemControlledProbe />
        </ThemeProvider>,
      )
      await user.click(screen.getByRole('button'))
      expect(screen.getByTestId('system-controlled').textContent).toBe('false')
    })
  })

  describe('reset-to-system flow', () => {
    function ResetHarness() {
      const { resetToSystem } = useTheme()
      return (
        <>
          <ThemeToggle />
          <button onClick={resetToSystem}>Reset to system</button>
          <SystemControlledProbe />
        </>
      )
    }

    it('clears localStorage when reset to system is triggered', async () => {
      localStorage.setItem(STORAGE_KEY, 'light')
      const user = userEvent.setup()
      render(
        <ThemeProvider>
          <ResetHarness />
        </ThemeProvider>,
      )

      await user.click(screen.getByRole('button', { name: 'Reset to system' }))
      expect(localStorage.getItem(STORAGE_KEY)).toBeNull()
    })

    it('marks isSystemControlled true again after reset', async () => {
      localStorage.setItem(STORAGE_KEY, 'light')
      const user = userEvent.setup()
      render(
        <ThemeProvider>
          <ResetHarness />
        </ThemeProvider>,
      )

      await user.click(screen.getByRole('button', { name: 'Reset to system' }))
      expect(screen.getByTestId('system-controlled').textContent).toBe('true')
    })

    it('reverts to the current system preference after reset, overriding the manual choice', async () => {
      mockMatchMedia(true) // system prefers light
      localStorage.setItem(STORAGE_KEY, 'dark')
      const user = userEvent.setup()
      render(
        <ThemeProvider>
          <ResetHarness />
        </ThemeProvider>,
      )

      const toggle = screen.getByRole('button', { name: /toggle/i })
      expect(toggle).toHaveAttribute('aria-pressed', 'true') // still dark before reset

      await user.click(screen.getByRole('button', { name: 'Reset to system' }))
      expect(toggle).toHaveAttribute('aria-pressed', 'false') // now follows system light
    })

    it('a manual toggle after reset persists again and stops following system', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider>
          <ResetHarness />
        </ThemeProvider>,
      )

      await user.click(screen.getByRole('button', { name: 'Reset to system' }))
      await user.click(screen.getByRole('button', { name: /toggle/i }))

      expect(screen.getByTestId('system-controlled').textContent).toBe('false')
      expect(localStorage.getItem(STORAGE_KEY)).not.toBeNull()
    })
  })
})
