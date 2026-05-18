import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Scanner from '../../../src/pages/Toolkit'
import { listPlugins } from '../../../src/api'

vi.mock('../../../src/api', () => ({
  listPlugins: vi.fn(),
}))

vi.mock('../../../src/data/scanTools', () => ({
  scanTools: [],
}))

const RECENT_TOOLS_STORAGE_KEY = 'secuscan_recent_tools'

function mockPlugins() {
  vi.mocked(listPlugins).mockResolvedValue({
    total: 7,
    plugins: [
      {
        id: 'tool_1',
        name: 'Tool One',
        description: 'First tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_2',
        name: 'Tool Two',
        description: 'Second tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_3',
        name: 'Tool Three',
        description: 'Third tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_4',
        name: 'Tool Four',
        description: 'Fourth tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_5',
        name: 'Tool Five',
        description: 'Fifth tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_6',
        name: 'Tool Six',
        description: 'Sixth tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
      {
        id: 'tool_7',
        name: 'Tool Seven',
        description: 'Seventh tool',
        category: 'recon',
        safety_level: 'safe',
        enabled: true,
        icon: '🛠️',
        requires_consent: false,
        consent_message: null,
        availability: { runnable: true, missing_binaries: [] },
      },
    ],
  })
}

describe('Scanner quick access', () => {
  beforeEach(() => {
    localStorage.clear()
    mockPlugins()
  })

  it('keeps rendering without the removed quick access section', async () => {
    localStorage.setItem(
      RECENT_TOOLS_STORAGE_KEY,
      JSON.stringify(['tool_7', 'tool_6', 'tool_5', 'tool_4', 'tool_3', 'tool_2', 'tool_1']),
    )

    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    expect(await screen.findByRole('tab', { name: /^Quick Start$/i })).toBeInTheDocument()
    expect(screen.queryByText(/Quick Access/i)).not.toBeInTheDocument()
    expect(screen.getByText(/No tools available in this category/i)).toBeInTheDocument()
  })

  it('updates recent tools when launching a tool', async () => {
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Scanner />
      </MemoryRouter>,
    )

    await user.click(await screen.findByRole('tab', { name: /Recon Tools/i }))
    await user.click(await screen.findByText(/Tool One/i))

    await waitFor(() => {
      const stored = JSON.parse(localStorage.getItem(RECENT_TOOLS_STORAGE_KEY) || '[]')
      expect(stored).toEqual(['tool_1'])
    })
  })
})
