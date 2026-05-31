import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import LiveLogViewer, { LogLine } from '../../../src/components/LiveLogViewer'

const stdoutLines: LogLine[] = [
  { line: 'Starting scan...', stream: 'stdout', ts: 1000 },
  { line: 'Connecting to target', stream: 'stdout', ts: 2000 },
]

const stderrLines: LogLine[] = [
  { line: 'Warning: timeout approaching', stream: 'stderr', ts: 3000 },
]

const mixedLines: LogLine[] = [...stdoutLines, ...stderrLines]

describe('LiveLogViewer', () => {
  it('renders stdout lines', () => {
    render(
      <LiveLogViewer
        lines={stdoutLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('Starting scan...')).toBeInTheDocument()
    expect(screen.getByText('Connecting to target')).toBeInTheDocument()
  })

  it('renders stderr lines with ERR badge', () => {
    render(
      <LiveLogViewer
        lines={stderrLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('Warning: timeout approaching')).toBeInTheDocument()
    expect(screen.getByText('ERR')).toBeInTheDocument()
  })

  it('shows stderr count badge when stderr lines exist', () => {
    render(
      <LiveLogViewer
        lines={mixedLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('1 Stderr')).toBeInTheDocument()
  })

  it('shows Live_Stream indicator when isLive is true', () => {
    render(
      <LiveLogViewer
        lines={[]}
        isLive={true}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('Live_Stream')).toBeInTheDocument()
  })

  it('does not show Live_Stream indicator when not live', () => {
    render(
      <LiveLogViewer
        lines={stdoutLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.queryByText('Live_Stream')).not.toBeInTheDocument()
  })

  it('shows awaiting output message when live with no lines', () => {
    render(
      <LiveLogViewer
        lines={[]}
        isLive={true}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('Awaiting_Output...')).toBeInTheDocument()
  })

  it('shows no output message when not live with no lines', () => {
    render(
      <LiveLogViewer
        lines={[]}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('No_Output_Available')).toBeInTheDocument()
  })

  it('filters lines by search input', async () => {
    render(
      <LiveLogViewer
        lines={mixedLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    const input = screen.getByPlaceholderText('Filter output...')
    fireEvent.change(input, { target: { value: 'Warning' } })
    expect(screen.getByText('Warning: timeout approaching')).toBeInTheDocument()
    expect(screen.queryByText('Starting scan...')).not.toBeInTheDocument()
  })

  it('calls onCopy when copy button clicked', () => {
    const onCopy = vi.fn()
    render(
      <LiveLogViewer
        lines={stdoutLines}
        isLive={false}
        onCopy={onCopy}
        copied={false}
      />
    )
    fireEvent.click(screen.getByText('Copy_Log'))
    expect(onCopy).toHaveBeenCalledOnce()
  })

  it('shows Copied label when copied is true', () => {
    render(
      <LiveLogViewer
        lines={stdoutLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={true}
      />
    )
    expect(screen.getByText('Copied')).toBeInTheDocument()
  })

  it('shows correct line count', () => {
    render(
      <LiveLogViewer
        lines={mixedLines}
        isLive={false}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    expect(screen.getByText('3 lines')).toBeInTheDocument()
  })

  it('toggles pause scroll button label', () => {
    render(
      <LiveLogViewer
        lines={stdoutLines}
        isLive={true}
        onCopy={vi.fn()}
        copied={false}
      />
    )
    const pauseBtn = screen.getByText('Pause_Scroll')
    fireEvent.click(pauseBtn)
    expect(screen.getByText('Resume_Scroll')).toBeInTheDocument()
  })
})