import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Reports from '../../../src/pages/Reports'
import { getReports, getDashboardSummary } from '../../../src/api'

vi.mock('../../../src/api', () => ({
    getReports: vi.fn(),
    getDashboardSummary: vi.fn(),
    API_BASE: 'http://127.0.0.1:8000',
}))

vi.spyOn(window, 'open').mockImplementation(() => null)

const readyReport = {
    id: 'report-1',
    task_id: 'task-abc-123',
    name: 'Security Scan — example.com',
    type: 'technical',
    generated_at: '2026-05-14T10:00:00Z',
    status: 'ready',
    findings: 7,
    assets: 3,
    pages: 12,
}

const emptySummary = {
    total_findings: 0,
    total_assets: 0,
    critical_findings: 0,
    high_findings: 0,
    total_attack_surface: 0,
}

function renderReports() {
    return render(
        <MemoryRouter>
            <Reports />
        </MemoryRouter>,
    )
}

beforeEach(() => {
    localStorage.clear()
    vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
})

describe('Reports — preferred export format', () => {
    it('saves preferred format to localStorage when export button is clicked', async () => {
        const user = userEvent.setup()
        renderReports()

        await user.click(await screen.findByRole('button', { name: /^pdf$/ }))

        expect(localStorage.getItem('secuscan:preferred-export-format')).toBe('pdf')
    })

    it('updates preferred format when a different format is clicked', async () => {
        const user = userEvent.setup()
        renderReports()

        await user.click(await screen.findByRole('button', { name: /^pdf$/ }))
        await user.click(screen.getByRole('button', { name: /^csv$/i }))

        expect(localStorage.getItem('secuscan:preferred-export-format')).toBe('csv')
    })

    it('highlights the preferred format button on load', async () => {
        localStorage.setItem('secuscan:preferred-export-format', 'html')
        renderReports()

        const htmlBtn = await screen.findByRole('button', { name: /^html$/i })

        expect(htmlBtn.className).toContain('bg-rag-amber')
    })

    it('preferred format button appears first', async () => {
        localStorage.setItem('secuscan:preferred-export-format', 'csv')
        renderReports()

        await screen.findByRole('button', { name: /^csv$/i })

        const buttons = screen.getAllByRole('button', { name: /^(pdf|html|csv)$/ })
        expect(buttons[0].textContent?.toLowerCase()).toBe('csv')
    })

    it('preference survives a remount (simulates page reload)', async () => {
        const user = userEvent.setup()
        const { unmount } = renderReports()

        await user.click(await screen.findByRole('button', { name: /^html$/i }))
        unmount()

        renderReports()

        const htmlBtn = await screen.findByRole('button', { name: /^html$/i })
        expect(htmlBtn.className).toContain('bg-rag-amber')
    })

    it('header download button uses the preferred format instead of defaulting to pdf', async () => {
        localStorage.setItem('secuscan:preferred-export-format', 'sarif')
        renderReports()

        const headerBtn = await screen.findByRole('button', { name: /download latest ready report sarif/i })
        await userEvent.click(headerBtn)

        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('/report/sarif'),
            '_blank',
        )
    })

    it('header download button defaults to pdf when no preference is saved', async () => {
        renderReports()

        const headerBtn = await screen.findByRole('button', { name: /download latest ready report pdf/i })
        await userEvent.click(headerBtn)

        expect(window.open).toHaveBeenCalledWith(
            expect.stringContaining('/report/pdf'),
            '_blank',
        )
    })
})