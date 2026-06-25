import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AppShell from '../../../src/components/AppShell'

vi.mock('../../../src/components/Sidebar', () => ({
  default: () => <aside data-testid="desktop-sidebar" />,
}))

vi.mock('../../../src/components/Background', () => ({
  default: () => <div data-testid="background" />,
}))

vi.mock('../../../src/hooks/useShortcuts', () => ({
  useShortcuts: vi.fn(),
}))

const renderShell = (initialPath = '/') =>
  render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route
          path="*"
          element={
            <AppShell>
              <section>Page content</section>
            </AppShell>
          }
        />
      </Routes>
    </MemoryRouter>
  )

describe('AppShell', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('opens and closes the mobile drawer from the menu controls', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))

    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument()
    })
  })

  it('closes the mobile drawer when the backdrop is clicked', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))
    expect(screen.getByRole('link', { name: 'Settings' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /close navigation menu/i }))

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument()
    })
  })

  it('locks page scroll while the mobile drawer is open', async () => {
    const user = userEvent.setup()
    renderShell()

    expect(document.body.style.overflow).toBe('')

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))
    expect(document.body.style.overflow).toBe('hidden')

    await user.click(screen.getByRole('button', { name: /close navigation menu/i }))
    await waitFor(() => {
      expect(document.body.style.overflow).toBe('')
    })
  })

  it('closes the mobile drawer when navigation changes routes', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))
    await user.click(screen.getByRole('link', { name: 'Settings' }))

    await waitFor(() => {
      expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument()
    })
    expect(screen.getByText('Page content')).toBeInTheDocument()
  })

  it('renders the mobile bottom navigation path shortcuts', () => {
    renderShell()

    expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /scans/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /findings/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /reports/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /workflows/i })).toBeInTheDocument()
  })
})


describe('AppShell mobile navigation focus trap', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('exposes the drawer as an accessible dialog when open', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))

    expect(screen.getByRole('dialog', { name: /navigation menu/i })).toBeInTheDocument()
  })

  it('closes the mobile menu when Escape is pressed', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))
    expect(screen.getByRole('dialog', { name: /navigation menu/i })).toBeInTheDocument()

    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog', { name: /navigation menu/i })).not.toBeInTheDocument()
  })

  it('sets aria-expanded on the hamburger button when menu is open', async () => {
    const user = userEvent.setup()
    renderShell()

    const button = screen.getByRole('button', { name: /toggle navigation menu/i })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })

  it('moves focus into the drawer when menu opens', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))

    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      const firstFocusable = dialog.querySelector('a, button')
      expect(document.activeElement).toBe(firstFocusable)
    })
  })

  it('returns focus to the hamburger button when menu closes via Escape', async () => {
    const user = userEvent.setup()
    renderShell()

    const button = screen.getByRole('button', { name: /toggle navigation menu/i })
    await user.click(button)
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(document.activeElement).toBe(button)
    })
  })

  it('traps Tab key focus within the drawer', async () => {
    const user = userEvent.setup()
    renderShell()

    await user.click(screen.getByRole('button', { name: /toggle navigation menu/i }))

    const dialog = screen.getByRole('dialog')
    const links = Array.from(dialog.querySelectorAll('a'))
    expect(links.length).toBeGreaterThan(1)

    await waitFor(() => {
      expect(document.activeElement).toBe(links[0])
    })

    for (let i = 1; i < links.length; i++) {
      await user.tab()
      expect(document.activeElement).toBe(links[i])
    }

    await user.tab()
    expect(document.activeElement).toBe(links[0])

    await user.tab({ shift: true })
    expect(document.activeElement).toBe(links[links.length - 1])
  })
})


describe('sidebar state synchronization', () => {
    beforeEach(() => {
        localStorage.clear()
    })

    it('responds to sidebar-state-changed custom event (same-tab)', async () => {
        renderShell()

        const main = document.querySelector('main')!
        // Default: expanded → --sidebar-width = 220px
        expect(main.style.getPropertyValue('--sidebar-width')).toBe('220px')

        // Collapse via custom event
        window.dispatchEvent(new CustomEvent('sidebar-state-changed', { detail: false }))
        await waitFor(() => {
            expect(main.style.getPropertyValue('--sidebar-width')).toBe('64px')
        })

        // Expand via custom event
        window.dispatchEvent(new CustomEvent('sidebar-state-changed', { detail: true }))
        await waitFor(() => {
            expect(main.style.getPropertyValue('--sidebar-width')).toBe('220px')
        })
    })

    it('responds to storage event (cross-tab)', async () => {
        renderShell()

        const main = document.querySelector('main')!

        // Simulate another tab writing to localStorage
        localStorage.setItem('sidebar-expanded', 'false')
        window.dispatchEvent(new Event('storage'))
        await waitFor(() => {
            expect(main.style.getPropertyValue('--sidebar-width')).toBe('64px')
        })

        localStorage.setItem('sidebar-expanded', 'true')
        window.dispatchEvent(new Event('storage'))
        await waitFor(() => {
            expect(main.style.getPropertyValue('--sidebar-width')).toBe('220px')
        })
    })
})