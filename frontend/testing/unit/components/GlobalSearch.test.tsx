import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import GlobalSearch from '../../../src/components/GlobalSearch'

vi.mock('../../../src/api', () => ({
  search: vi.fn(),
}))

import { search } from '../../../src/api'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<any>()
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

function renderSearch() {
  return render(
    <MemoryRouter>
      <GlobalSearch />
    </MemoryRouter>,
  )
}

describe('GlobalSearch', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the search input', () => {
    renderSearch()
    expect(screen.getByLabelText('Global search')).toBeInTheDocument()
  })

  it('does not call search for an empty query', async () => {
    renderSearch()
    await new Promise((r) => setTimeout(r, 350))
    expect(search).not.toHaveBeenCalled()
  })

  it('debounces and calls search after typing', async () => {
    vi.mocked(search).mockResolvedValue({
      query: 'sql',
      findings: [
        { id: 'f1', title: 'SQL Injection', category: 'Injection', severity: 'critical', target: 'example.com' },
      ],
      reports: [],
      total: 1,
    })

    renderSearch()
    const input = screen.getByLabelText('Global search')
    await userEvent.type(input, 'sql')

    await waitFor(() => expect(search).toHaveBeenCalledWith('sql'), { timeout: 1000 })
    expect(await screen.findByText('SQL Injection')).toBeInTheDocument()
  })

  it('shows a no-results message when nothing matches', async () => {
    vi.mocked(search).mockResolvedValue({ query: 'zzz', findings: [], reports: [], total: 0 })

    renderSearch()
    await userEvent.type(screen.getByLabelText('Global search'), 'zzz')

    await waitFor(() => expect(search).toHaveBeenCalled(), { timeout: 1000 })
    expect(await screen.findByText(/No results for "zzz"/i)).toBeInTheDocument()
  })

  it('shows an error message when the search request fails', async () => {
    vi.mocked(search).mockRejectedValue(new Error('network error'))

    renderSearch()
    await userEvent.type(screen.getByLabelText('Global search'), 'fail')

    await waitFor(() => expect(search).toHaveBeenCalled(), { timeout: 1000 })
    expect(await screen.findByText(/Search failed/i)).toBeInTheDocument()
  })

  it('navigates to the findings page when a finding result is clicked', async () => {
    vi.mocked(search).mockResolvedValue({
      query: 'sql',
      findings: [
        { id: 'f1', title: 'SQL Injection', category: 'Injection', severity: 'critical', target: 'example.com' },
      ],
      reports: [],
      total: 1,
    })

    renderSearch()
    await userEvent.type(screen.getByLabelText('Global search'), 'sql')

    const result = await screen.findByText('SQL Injection')
    await userEvent.click(result)

    expect(mockNavigate).toHaveBeenCalledWith('/findings')
  })

  it('closes the dropdown on Escape', async () => {
    vi.mocked(search).mockResolvedValue({ query: 'sql', findings: [], reports: [], total: 0 })

    renderSearch()
    await userEvent.type(screen.getByLabelText('Global search'), 'sql')
    await waitFor(() => expect(search).toHaveBeenCalled(), { timeout: 1000 })
    expect(await screen.findByRole('listbox', { name: /search results/i })).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    await waitFor(() =>
      expect(screen.queryByRole('listbox', { name: /search results/i })).not.toBeInTheDocument(),
    )
  })
})