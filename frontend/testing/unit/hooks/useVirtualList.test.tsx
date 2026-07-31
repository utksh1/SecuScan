import React from 'react'
import { render, fireEvent, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useVirtualList } from '../../../src/hooks/useVirtualList'

// @tanstack/react-virtual needs ResizeObserver + a measurable scroll container in jsdom.
// Same setup used by testing/unit/pages/Findings.test.tsx for the other virtualized list.
if (typeof global.ResizeObserver === 'undefined') {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any
}

Object.defineProperty(HTMLElement.prototype, 'scrollHeight', { configurable: true, value: 4000 })
Object.defineProperty(HTMLElement.prototype, 'offsetHeight', { configurable: true, value: 600 })

interface Captured {
  virtualItems: ReturnType<typeof useVirtualList>['virtualItems']
  totalSize: number
}

// Minimal harness that mounts the hook the way real consumers do: attach
// parentRef to the scrollable container so the virtualizer can measure it.
// Results are stashed on a plain (non-React-state) ref so assertions can
// read the latest values after each render/act without an extra rerender.

function Harness({
  items,
  estimateSize,
  overscan,
  captured,
}: {
  items: string[]
  estimateSize: number | ((index: number) => number)
  overscan?: number
  captured: { current: Captured }
}) {
  const { parentRef, virtualItems, totalSize } = useVirtualList({
    items,
    estimateSize,
    overscan,
  })
  captured.current = { virtualItems, totalSize }

  return (
    <div ref={parentRef} data-testid="scroll-container" style={{ height: 600, overflow: 'auto' }}>
      <div style={{ height: totalSize, position: 'relative', width: '100%' }}>
        {virtualItems.map((vItem) => (
          <div key={vItem.key} data-testid="virtual-row" data-index={vItem.index} />
        ))}
      </div>
    </div>
  )
}

function makeItems(count: number) {
  return Array.from({ length: count }, (_, i) => `item-${i}`)
}

function makeCaptured(): { current: Captured } {
  return { current: { virtualItems: [], totalSize: 0 } }
}

describe('useVirtualList', () => {
  it('calculates the default visible range for a populated list', () => {
    const captured = makeCaptured()
    const items = makeItems(100)

    render(<Harness items={items} estimateSize={40} captured={captured} />)

    // 100 rows * 40px estimated height = 4000px of total scrollable size
    expect(captured.current.totalSize).toBe(4000)

    // Container is 600px tall with 40px rows, so only a subset (+ overscan)
    // should be rendered, not the entire 100-item list.
    expect(captured.current.virtualItems.length).toBeGreaterThan(0)
    expect(captured.current.virtualItems.length).toBeLessThan(items.length)

    // The initial range starts at the top of the list.
    expect(captured.current.virtualItems[0].index).toBe(0)
  })

  it('shifts the visible range forward when the container scrolls down', () => {
    const captured = makeCaptured()
    const items = makeItems(100)

    const { getByTestId } = render(
      <Harness items={items} estimateSize={40} captured={captured} />,
    )

    const firstIndexBeforeScroll = captured.current.virtualItems[0].index

    const container = getByTestId('scroll-container')
    act(() => {
      Object.defineProperty(container, 'scrollTop', { configurable: true, value: 2000 })
      fireEvent.scroll(container)
    })

    const firstIndexAfterScroll = captured.current.virtualItems[0].index

    // Scrolling ~2000px down through 40px rows should move the visible
    // window well past the first item.
    expect(firstIndexAfterScroll).toBeGreaterThan(firstIndexBeforeScroll)
  })

  it('returns an empty range and zero total size for an empty list', () => {
    const captured = makeCaptured()

    render(<Harness items={[]} estimateSize={40} captured={captured} />)

    expect(captured.current.totalSize).toBe(0)
    expect(captured.current.virtualItems).toHaveLength(0)
  })

  it('respects a custom overscan value', () => {
    const items = makeItems(50)

    const smallOverscan = makeCaptured()
    render(<Harness items={items} estimateSize={40} overscan={0} captured={smallOverscan} />)

    const largeOverscan = makeCaptured()
    render(<Harness items={items} estimateSize={40} overscan={20} captured={largeOverscan} />)

    // A larger overscan should never render fewer rows than a smaller one
    // for the same list and viewport.
    expect(largeOverscan.current.virtualItems.length).toBeGreaterThanOrEqual(
      smallOverscan.current.virtualItems.length,
    )
    // Total scrollable size only depends on item count/size, not overscan.
    expect(smallOverscan.current.totalSize).toBe(2000)
    expect(largeOverscan.current.totalSize).toBe(2000)
  })

  it('supports a per-index size function instead of a fixed number', () => {
    const captured = makeCaptured()
    const items = makeItems(10)

    // Alternate 20px / 60px rows: 5 * 20 + 5 * 60 = 400px total.
    const estimateSize = (index: number) => (index % 2 === 0 ? 20 : 60)

    render(<Harness items={items} estimateSize={estimateSize} captured={captured} />)

    expect(captured.current.totalSize).toBe(400)
  })
})