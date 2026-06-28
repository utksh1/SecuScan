import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import Settings from '../../../src/pages/Settings'
import { ThemeProvider } from '../../../src/components/ThemeContext'
import { ToastProvider } from '../../../src/components/ToastContext'
import { listNotificationRules } from '../../../src/api'

vi.mock('../../../src/api', async () => {
  const actual: any = await vi.importActual('../../../src/api')
  return {
    ...actual,
    listNotificationRules: vi.fn(),
  }
})

function renderSettings() {
  render(
    <ThemeProvider>
      <ToastProvider>
        <Settings />
      </ToastProvider>
    </ThemeProvider>,
  )
}

describe('Settings export flow', () => {
  beforeEach(() => {
    localStorage.removeItem('secuscan-config')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })

  it('creates a download anchor with a JSON data URI and clicks it', async () => {
    const user = userEvent.setup()
    renderSettings()

    const createdAnchors: HTMLAnchorElement[] = []
    const originalCreate = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreate(tag)
      if (tag === 'a') {
        vi.spyOn(el as HTMLAnchorElement, 'click').mockImplementation(() => {})
        createdAnchors.push(el as HTMLAnchorElement)
      }
      return el
    })

    await user.click(screen.getByRole('button', { name: /TELEMETRY_EXPORT/i }))

    expect(createdAnchors).toHaveLength(1)
    const anchor = createdAnchors[0]

    expect(anchor.getAttribute('href')).toMatch(/^data:text\/json/)
    expect(anchor.click).toHaveBeenCalledOnce()

    vi.restoreAllMocks()
  })

  it('sets the download filename to secuscan_config_<today>.json', async () => {
    const user = userEvent.setup()
    renderSettings()

    const createdAnchors: HTMLAnchorElement[] = []
    const originalCreate = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreate(tag)
      if (tag === 'a') {
        vi.spyOn(el as HTMLAnchorElement, 'click').mockImplementation(() => {})
        createdAnchors.push(el as HTMLAnchorElement)
      }
      return el
    })

    await user.click(screen.getByRole('button', { name: /TELEMETRY_EXPORT/i }))

    const today = new Date().toISOString().split('T')[0]
    expect(createdAnchors[0].getAttribute('download')).toBe(
      `secuscan_config_${today}.json`,
    )

    vi.restoreAllMocks()
  })

  it('exports a valid JSON string containing the current config', async () => {
    const user = userEvent.setup()
    renderSettings()

    const createdAnchors: HTMLAnchorElement[] = []
    const originalCreate = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreate(tag)
      if (tag === 'a') {
        vi.spyOn(el as HTMLAnchorElement, 'click').mockImplementation(() => {})
        createdAnchors.push(el as HTMLAnchorElement)
      }
      return el
    })

    await user.click(screen.getByRole('button', { name: /TELEMETRY_EXPORT/i }))

    const href = createdAnchors[0].getAttribute('href') ?? ''
    const jsonStr = decodeURIComponent(
      href.replace('data:text/json;charset=utf-8,', ''),
    )
    const exported = JSON.parse(jsonStr)

    expect(exported.concurrentScans).toBe(8)
    expect(exported.scanIntensity).toBe('standard')
    expect(exported.theme).toBe('dark')

    vi.restoreAllMocks()
  })

  it('removes the anchor from the DOM after the download is triggered', async () => {
    const user = userEvent.setup()
    renderSettings()

    const createdAnchors: HTMLAnchorElement[] = []
    const originalCreate = document.createElement.bind(document)

    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreate(tag)
      if (tag === 'a') {
        vi.spyOn(el as HTMLAnchorElement, 'click').mockImplementation(() => {})
        createdAnchors.push(el as HTMLAnchorElement)
      }
      return el
    })

    await user.click(screen.getByRole('button', { name: /TELEMETRY_EXPORT/i }))

    expect(document.body.contains(createdAnchors[0])).toBe(false)

    vi.restoreAllMocks()
  })
})

describe('Management Tools button overflow fix', () => {
  beforeEach(() => {
    localStorage.removeItem('secuscan-config')
    vi.mocked(listNotificationRules).mockResolvedValue([])
  })

  it('renders all three management tool buttons', () => {
    renderSettings()
    expect(screen.getByRole('button', { name: /TELEMETRY_EXPORT/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ENGINE_RESET/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /NUCLEAR_PURGE/i })).toBeInTheDocument()
  })

  it('TELEMETRY_EXPORT button does not use overflow-breaking letter-spacing class', () => {
    renderSettings()
    const btn = screen.getByRole('button', { name: /TELEMETRY_EXPORT/i })
    expect(btn.className).not.toContain('tracking-[0.3em]')
    expect(btn.className).toContain('tracking-[0.08em]')
    expect(btn.className).toContain('whitespace-nowrap')
    expect(btn.className).toContain('overflow-hidden')
  })

  it('ENGINE_RESET button does not use overflow-breaking letter-spacing class', () => {
    renderSettings()
    const btn = screen.getByRole('button', { name: /ENGINE_RESET/i })
    expect(btn.className).not.toContain('tracking-[0.3em]')
    expect(btn.className).toContain('tracking-[0.08em]')
    expect(btn.className).toContain('whitespace-nowrap')
    expect(btn.className).toContain('overflow-hidden')
  })

  it('NUCLEAR_PURGE button does not use overflow-breaking letter-spacing class', () => {
    renderSettings()
    const btn = screen.getByRole('button', { name: /NUCLEAR_PURGE/i })
    expect(btn.className).not.toContain('tracking-[0.3em]')
    expect(btn.className).toContain('tracking-[0.08em]')
    expect(btn.className).toContain('whitespace-nowrap')
    expect(btn.className).toContain('overflow-hidden')
  })
})
