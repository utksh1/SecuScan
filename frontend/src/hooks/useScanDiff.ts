import { useState, useCallback, useRef } from 'react'
import { getScanDiff } from '../api'
import type { ScanDiffResponse } from '../api'

export function useScanDiff() {
  const [data, setData] = useState<ScanDiffResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const fetchDiff = useCallback(async (scanAId: string, scanBId: string): Promise<void> => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setIsLoading(true)
    setError(null)
    try {
      const result = await getScanDiff(scanAId, scanBId)
      if (!controller.signal.aborted) {
        setData(result)
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e instanceof Error ? e.message : 'Unknown error')
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false)
      }
    }
  }, [])

  function reset(): void {
    abortRef.current?.abort()
    abortRef.current = null
    setData(null)
    setError(null)
    setIsLoading(false)
  }

  return { data, isLoading, error, fetchDiff, reset }
}
