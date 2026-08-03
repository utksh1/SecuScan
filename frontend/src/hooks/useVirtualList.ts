import { useRef } from 'react'
import { useVirtualizer, type VirtualizerOptions } from '@tanstack/react-virtual'

export interface UseVirtualListOptions<T>
  extends Partial<
    Omit<
      VirtualizerOptions<HTMLDivElement, Element>,
      'count' | 'getScrollElement' | 'estimateSize'
    >
  > {
  items: T[]
  estimateSize: number | ((index: number) => number)
  overscan?: number
}

/**
 * Thin wrapper around @tanstack/react-virtual's useVirtualizer.
 *
 * Returns:
 *  - `parentRef`     — attach to the scrollable container div
 *  - `virtualizer`   — the virtualizer instance
 *  - `virtualItems`  — the currently visible virtual items
 *  - `totalSize`     — total scrollable height in px
 */
export function useVirtualList<T>({
  items,
  estimateSize,
  overscan = 5,
  ...rest
}: UseVirtualListOptions<T>) {
  const parentRef = useRef<HTMLDivElement>(null)

  const estimateFn =
    typeof estimateSize === 'number' ? () => estimateSize : estimateSize

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: estimateFn,
    overscan,
    ...rest,
  })

  return {
    parentRef,
    virtualizer,
    virtualItems: virtualizer.getVirtualItems(),
    totalSize: virtualizer.getTotalSize(),
  }
}