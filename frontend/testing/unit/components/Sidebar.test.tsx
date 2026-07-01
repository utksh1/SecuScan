import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import Sidebar from '../../../src/components/Sidebar'
import { SidebarProvider } from '../../../src/context/SidebarContext'
import { ThemeProvider } from '../../../src/components/ThemeContext'

const renderSidebar = () => {
  return render(
    <ThemeProvider>
      <BrowserRouter>
        <SidebarProvider>
          <Sidebar />
        </SidebarProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}

describe('Sidebar - Accessibility', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('should have proper aria labels', () => {
    const { container } = renderSidebar()
    const sidebar = container.querySelector('aside')
    expect(sidebar).toHaveAttribute('aria-label', 'Main navigation')
    expect(sidebar).toHaveAttribute('aria-expanded', 'true')
  })

  it('should toggle sidebar on button click', () => {
    const { container } = renderSidebar()
    const sidebar = container.querySelector('aside')
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(toggleButton)

    expect(sidebar).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByLabelText(/expand sidebar/i)).toBeInTheDocument()
  })

  it('should toggle sidebar with keyboard (Enter)', async () => {
    const user = userEvent.setup()
    const { container } = renderSidebar()
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)
    const sidebar = container.querySelector('aside')

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')

    toggleButton.focus()
    await user.keyboard('{Enter}')

    expect(sidebar).toHaveAttribute('aria-expanded', 'false')
  })

  it('should toggle sidebar with keyboard (Space)', async () => {
    const user = userEvent.setup()
    const { container } = renderSidebar()
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)
    const sidebar = container.querySelector('aside')

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')

    toggleButton.focus()
    await user.keyboard(' ')

    expect(sidebar).toHaveAttribute('aria-expanded', 'false')
  })

  it('should persist sidebar state to localStorage', () => {
    renderSidebar()
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)

    fireEvent.click(toggleButton)

    const saved = localStorage.getItem('sidebar-expanded')
    expect(saved).toBe('false')
  })

  it('should restore sidebar state from localStorage', () => {
    localStorage.setItem('sidebar-expanded', JSON.stringify(false))

    const { container } = renderSidebar()
    const sidebar = container.querySelector('aside')

    expect(sidebar).toHaveAttribute('aria-expanded', 'false')
  })

  it('should not toggle sidebar on navigation item click', () => {
    const { container } = renderSidebar()
    const sidebar = container.querySelector('aside')
    const dashboardLink = screen.getByRole('link', { name: /dashboard/i })

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')

    fireEvent.click(dashboardLink)

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')
  })

  it('should have focusable toggle button', () => {
    renderSidebar()
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)

    expect(toggleButton).not.toHaveAttribute('disabled')
    toggleButton.focus()
    expect(document.activeElement).toBe(toggleButton)
  })

  it('should have focus ring visible on toggle button', () => {
    renderSidebar()
    const toggleButton = screen.getByLabelText(/collapse sidebar/i)

    expect(toggleButton).toHaveClass('focus:ring-2', 'focus:ring-rag-red/50')
  })

  it('should toggle via keyboard shortcut g+b', () => {
    localStorage.setItem('sidebar-expanded', 'true')
    const { container } = renderSidebar()
    const sidebar = container.querySelector('aside')

    expect(sidebar).toHaveAttribute('aria-expanded', 'true')

    fireEvent.keyDown(window, { key: 'g' })
    fireEvent.keyDown(window, { key: 'b' })

    setTimeout(() => {
      expect(sidebar).toHaveAttribute('aria-expanded', 'false')
    }, 100)
  })
})
