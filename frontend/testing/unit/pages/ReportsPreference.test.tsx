import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Reports from '../../../src/pages/Reports'
import * as api from '../../../src/api'

// Simple mocks for complex UI components
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    section: ({ children, ...props }: any) => <section {...props}>{children}</section>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('@hugeicons/react', () => ({
  HugeiconsIcon: () => <span data-testid="hugeicons-icon" />,
}))

vi.mock('../../../src/api', () => ({
  getReports: vi.fn(),
  getDashboardSummary: vi.fn(),
  API_BASE: 'http://test-api',
}))

describe('Reports page preference integration', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.getReports).mockResolvedValue({ reports: [] })
    vi.mocked(api.getDashboardSummary).mockResolvedValue({})
  })

  it('persists selected report type filter', async () => {
    const user = userEvent.setup()

    const { unmount } = render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    )

    // Initially 'all'
    const techButton = screen.getByRole('button', { name: /technical BRIEFINGS/i })
    await user.click(techButton)

    // Check localStorage
    expect(localStorage.getItem('secuscan-pref:reports-type-filter')).toContain('technical')

    unmount()

    // Re-render and check if it's still 'technical'
    render(
      <MemoryRouter>
        <Reports />
      </MemoryRouter>
    )

    expect(screen.getByRole('button', { name: /technical BRIEFINGS/i })).toHaveClass('bg-rag-red')
  })
})
