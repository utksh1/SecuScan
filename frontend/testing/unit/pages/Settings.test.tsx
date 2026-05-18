import { render, screen, fireEvent } from '@testing-library/react'
import { vi } from 'vitest'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'

describe('Settings', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('saves config to localStorage when save is clicked', () => {
    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>
    )
    fireEvent.click(screen.getByText(/COMMIT_ENGINE_CHANGES/i))
    
    const stored = JSON.parse(localStorage.getItem('secuscan-config') ?? '{}')
    expect(stored.concurrentScans).toBeDefined()
    expect(stored.scanIntensity).toBe('standard')
  })

  it('resets to defaults when user confirms reset', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    localStorage.setItem('secuscan-config', JSON.stringify({ concurrentScans: 50 }))
    
    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>
    )
    fireEvent.click(screen.getByText(/ENGINE_RESET/i))

    const stored = JSON.parse(localStorage.getItem('secuscan-config') ?? '{}')
    expect(stored.concurrentScans).toBe(8)
  })

  it('does not reset if user cancels', () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    localStorage.setItem('secuscan-config', JSON.stringify({ concurrentScans: 50 }))
    
    render(
      <ThemeProvider>
        <ToastProvider>
          <Settings />
        </ToastProvider>
      </ThemeProvider>
    )
    fireEvent.click(screen.getByText(/ENGINE_RESET/i))

    const stored = JSON.parse(localStorage.getItem('secuscan-config') ?? '{}')
    expect(stored.concurrentScans).toBe(50)
  })
})