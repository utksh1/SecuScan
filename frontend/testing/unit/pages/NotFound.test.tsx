import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import NotFound from '../../../src/pages/NotFound'
import { routes } from '../../../src/routes'

// Mock the ThemeContext
const mockUseTheme = vi.fn()
vi.mock('../../../src/components/ThemeContext', () => ({
  useTheme: () => mockUseTheme(),
}))

describe('NotFound Page', () => {
  it('renders the 404 heading and error message', () => {
    mockUseTheme.mockReturnValue({ theme: 'light' })
    render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    expect(screen.getByRole('heading', { name: '404' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Page Not Found/i })).toBeInTheDocument()
    expect(screen.getByText(/The requested page does not exist/i)).toBeInTheDocument()
  })

  it('renders the return to dashboard link correctly', () => {
    mockUseTheme.mockReturnValue({ theme: 'light' })
    render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    const link = screen.getByRole('link', { name: /Return to Dashboard/i })
    expect(link).toBeInTheDocument()
    expect(link.getAttribute('href')).toBe(routes.dashboard)
  })

  it('applies dark theme styling when theme is dark', () => {
    mockUseTheme.mockReturnValue({ theme: 'dark' })
    const { container } = render(
      <BrowserRouter>
        <NotFound />
      </BrowserRouter>
    )

    // The top level div gets 'bg-charcoal-dark' when dark theme is applied
    expect(container.firstChild).toHaveClass('bg-charcoal-dark')
    // Verify 404 text color adapts to dark mode
    expect(screen.getByRole('heading', { name: '404' })).toHaveClass('text-silver-bright')
  })
})
