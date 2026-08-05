import { render, screen } from '@testing-library/react'
import ScanTimeline from '../../../src/components/ScanTimeline'

describe('ScanTimeline', () => {
  it('renders the queued state with the first stage active and the rest pending', () => {
    render(<ScanTimeline status="queued" />)

    expect(screen.getByText('Live Scan Timeline')).toBeInTheDocument()
    expect(screen.getByText('Target Queued')).toBeInTheDocument()
    expect(screen.getByText('Scan Executing')).toBeInTheDocument()
    expect(screen.getByText('Report Generation')).toBeInTheDocument()

    // Stage 2 and 3 should show their pending index numbers since nothing is completed yet
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders the running state with the first stage completed and the second active', () => {
    render(<ScanTimeline status="running" latestOutputLine="Scanning port 443..." />)

    expect(screen.getByText('✓')).toBeInTheDocument()
    expect(screen.getByText('Scanning port 443...')).toBeInTheDocument()
    // Stage 3 still pending
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders the completed state with all three stages marked complete', () => {
    render(<ScanTimeline status="completed" />)

    const checks = screen.getAllByText('✓')
    expect(checks).toHaveLength(3)
  })

  it('renders the failed state with the second stage marked failed', () => {
    render(<ScanTimeline status="failed" />)

    expect(screen.getByText('✓')).toBeInTheDocument()
    expect(screen.getByText('✕')).toBeInTheDocument()
    // Final stage remains pending
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('renders the cancelled state the same way as failed, with the second stage marked failed', () => {
    render(<ScanTimeline status="cancelled" />)

    expect(screen.getByText('✓')).toBeInTheDocument()
    expect(screen.getByText('✕')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('does not show the latest output line when no stage is active', () => {
    render(<ScanTimeline status="completed" latestOutputLine="Should not render" />)

    expect(screen.queryByText('Should not render')).not.toBeInTheDocument()
  })
})