import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { vi, describe, it, expect } from 'vitest'
import Reports from '../../../src/pages/Reports'

// ─── Mock API ────────────────────────────────────────────────────────────────
vi.mock('../../../src/api', () => ({
  getReports: vi.fn().mockResolvedValue({
    reports: [
      {
        id: '1',
        task_id: 't1',
        name: 'Alpha Report',
        type: 'executive',
        status: 'ready',
        generated_at: new Date().toISOString(),                           // now → within 24h
        findings: 5,
        assets: 10,
        pages: 3,
      },
      {
        id: '2',
        task_id: 't2',
        name: 'Beta Report',
        type: 'technical',
        status: 'failed',
        generated_at: new Date(Date.now() - 2 * 86400000).toISOString(), // 2 days ago → outside 24h, inside 7d
        findings: 2,
        assets: 4,
        pages: 1,
      },
      {
        id: '3',
        task_id: 't3',
        name: 'Gamma Report',
        type: 'compliance',
        status: 'generating',
        generated_at: new Date(Date.now() - 10 * 86400000).toISOString(), // 10 days ago → outside 7d, inside 30d
        findings: 0,
        assets: 2,
        pages: 0,
      },
    ],
  }),
  getDashboardSummary: vi.fn().mockResolvedValue({
    total_findings: 7,
    total_assets: 16,
    critical_findings: 1,
    high_findings: 2,
    total_attack_surface: 0,
  }),
  API_BASE: 'http://localhost:8000',
}))

// ─── Helper ───────────────────────────────────────────────────────────────────
function renderReports() {
  return render(
    <MemoryRouter>
      <Reports />
    </MemoryRouter>
  )
}

// ─── Tests ────────────────────────────────────────────────────────────────────
describe('Reports page – status filter', () => {
  it('shows all reports by default', async () => {
    renderReports()
    expect(await screen.findByText('Alpha Report')).toBeInTheDocument()
    expect(screen.getByText('Beta Report')).toBeInTheDocument()
    expect(screen.getByText('Gamma Report')).toBeInTheDocument()
  })

  it('shows only ready reports when status filter is "Ready"', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /status ready/i }))
    expect(await screen.findByText('Alpha Report')).toBeInTheDocument()
    expect(screen.queryByText('Beta Report')).not.toBeInTheDocument()
    expect(screen.queryByText('Gamma Report')).not.toBeInTheDocument()
  })

  it('shows only failed reports when status filter is "Failed"', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /status failed/i }))
    expect(await screen.findByText('Beta Report')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Report')).not.toBeInTheDocument()
    expect(screen.queryByText('Gamma Report')).not.toBeInTheDocument()
  })

  it('shows only generating reports when status filter is "Generating"', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /status generating/i }))
    expect(await screen.findByText('Gamma Report')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Report')).not.toBeInTheDocument()
    expect(screen.queryByText('Beta Report')).not.toBeInTheDocument()
  })
})

describe('Reports page – date range filter', () => {
  it('shows only reports from the last 24 hours', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /date last 24 hours/i }))
    expect(await screen.findByText('Alpha Report')).toBeInTheDocument()   // now
    expect(screen.queryByText('Beta Report')).not.toBeInTheDocument()     // 2 days ago
    expect(screen.queryByText('Gamma Report')).not.toBeInTheDocument()    // 10 days ago
  })

  it('shows reports from the last 7 days', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /date last 7 days/i }))
    expect(await screen.findByText('Alpha Report')).toBeInTheDocument()   // now
    expect(screen.getByText('Beta Report')).toBeInTheDocument()           // 2 days ago
    expect(screen.queryByText('Gamma Report')).not.toBeInTheDocument()    // 10 days ago
  })
})

describe('Reports page – combined filters', () => {
  it('combined type + status filter works correctly', async () => {
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /technical briefings/i }))
    fireEvent.click(screen.getByRole('button', { name: /status failed/i }))
    expect(await screen.findByText('Beta Report')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Report')).not.toBeInTheDocument()
  })

  it('shows empty state when combined status + date filters match nothing', async () => {
    renderReports()
    // "failed" (Beta Report, 2 days ago) + "24h" → nothing matches
    fireEvent.click(await screen.findByRole('button', { name: /status failed/i }))
    fireEvent.click(screen.getByRole('button', { name: /date last 24 hours/i }))
    expect(await screen.findByText(/archive isolated/i)).toBeInTheDocument()
    expect(screen.getByText(/no entries match the selected filters/i)).toBeInTheDocument()
  })

  it('entry count updates correctly when filters are applied', async () => {
    renderReports()
    expect(await screen.findByText('3 ENTRIES_LOCATED')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /status ready/i }))
    await waitFor(() => {
      expect(screen.getByText('1 ENTRIES_LOCATED')).toBeInTheDocument()
    })
  })

  it('export buttons remain functional on filtered reports', async () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)
    renderReports()
    fireEvent.click(await screen.findByRole('button', { name: /status ready/i }))
    const pdfButton = await screen.findByTitle('Download PDF')
    fireEvent.click(pdfButton)
    expect(openSpy).toHaveBeenCalledWith(
      'http://localhost:8000/task/t1/report/pdf',
      '_blank'
    )
    openSpy.mockRestore()
  })
})