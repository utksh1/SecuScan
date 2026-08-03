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
    vi.mocked(getDashboardSummary).mockResolvedValue(emptySummary)
})

describe('Reports — onboarding empty state', () => {
    it('shows the onboarding message when there are zero reports', async () => {
        vi.mocked(getReports).mockResolvedValue({ reports: [] })
        renderReports()

        expect(await screen.findByText(/No Briefings Yet/i)).toBeInTheDocument()
        expect(screen.getByText(/Run a scan from the Toolkit/i)).toBeInTheDocument()
    })

    it('shows a call-to-action link pointing to the toolkit route', async () => {
        vi.mocked(getReports).mockResolvedValue({ reports: [] })
        renderReports()

        const cta = await screen.findByRole('link', { name: /launch_first_scan/i })
        expect(cta).toHaveAttribute('href', '/toolkit')
    })

    it('does not show the onboarding message when reports exist but filters hide them all', async () => {
        const user = userEvent.setup()
        vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
        renderReports()

        await screen.findByText(/Security Scan — example.com/i)
        await user.click(screen.getByRole('button', { name: /executive briefings/i }))

        expect(screen.queryByText(/No Briefings Yet/i)).not.toBeInTheDocument()
        expect(await screen.findByText(/Archive Isolated/i)).toBeInTheDocument()
    })

    it('does not show the onboarding empty state once reports are loaded', async () => {
        vi.mocked(getReports).mockResolvedValue({ reports: [readyReport] })
        renderReports()

        await screen.findByText(/Security Scan — example.com/i)

        expect(screen.queryByText(/No Briefings Yet/i)).not.toBeInTheDocument()
        expect(screen.queryByRole('link', { name: /launch_first_scan/i })).not.toBeInTheDocument()
    })
})