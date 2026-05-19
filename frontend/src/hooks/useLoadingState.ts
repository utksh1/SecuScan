import { useState, useCallback, useRef, useEffect } from 'react'

interface UseLoadingStateOptions {
  delay?: number // Delay before showing loading state
  minDuration?: number // Minimum time to show loading state
}

interface UseLoadingStateReturn {
  isLoading: boolean
  isInitialLoad: boolean
  error: string | null
  startLoading: () => void
  stopLoading: (error?: string | null) => void
  setError: (error: string | null) => void
  reset: () => void
}

/**
 * Custom hook for managing loading states with built-in delay and minimum duration
 * Prevents UI flickering by delaying the loading state display
 */
export function useLoadingState(
  options: UseLoadingStateOptions = {}
): UseLoadingStateReturn {
  const { delay = 300, minDuration = 500 } = options
  
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialLoad, setIsInitialLoad] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const delayTimerRef = useRef<NodeJS.Timeout | null>(null)
  const minDurationTimerRef = useRef<NodeJS.Timeout | null>(null)
  const loadingStartTimeRef = useRef<number>(0)

  const startLoading = useCallback(() => {
    // Clear any existing timers
    if (delayTimerRef.current) clearTimeout(delayTimerRef.current)
    if (minDurationTimerRef.current) clearTimeout(minDurationTimerRef.current)

    setError(null)
    loadingStartTimeRef.current = Date.now()

    // Delay loading state to prevent flickering on fast operations
    delayTimerRef.current = setTimeout(() => {
      setIsLoading(true)
      setIsInitialLoad(false)
    }, delay)
  }, [delay])

  const stopLoading = useCallback((error: string | null = null) => {
    // Clear delay timer if loading hasn't started yet
    if (delayTimerRef.current) {
      clearTimeout(delayTimerRef.current)
      delayTimerRef.current = null
    }

    if (error) {
      setError(error)
      setIsLoading(false)
      setIsInitialLoad(false)
      return
    }

    // Calculate elapsed time and ensure minimum duration
    const elapsed = Date.now() - loadingStartTimeRef.current
    const remainingTime = Math.max(0, minDuration - elapsed)

    if (remainingTime > 0) {
      minDurationTimerRef.current = setTimeout(() => {
        setIsLoading(false)
        setIsInitialLoad(false)
      }, remainingTime)
    } else {
      setIsLoading(false)
      setIsInitialLoad(false)
    }
  }, [minDuration])

  const resetState = useCallback(() => {
    if (delayTimerRef.current) clearTimeout(delayTimerRef.current)
    if (minDurationTimerRef.current) clearTimeout(minDurationTimerRef.current)

    setIsLoading(false)
    setIsInitialLoad(true)
    setError(null)
  }, [])

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (delayTimerRef.current) clearTimeout(delayTimerRef.current)
      if (minDurationTimerRef.current) clearTimeout(minDurationTimerRef.current)
    }
  }, [])

  return {
    isLoading,
    isInitialLoad,
    error,
    startLoading,
    stopLoading,
    setError,
    reset: resetState
  }
}

/**
 * Custom hook for handling async operations with automatic loading state management
 */
export function useAsyncLoading<T>(
  asyncFn: () => Promise<T>,
  options: UseLoadingStateOptions = {}
) {
  const loadingState = useLoadingState(options)
  const [data, setData] = useState<T | null>(null)

  const execute = useCallback(async () => {
    loadingState.startLoading()
    try {
      const result = await asyncFn()
      setData(result)
      loadingState.stopLoading()
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      loadingState.stopLoading(errorMessage)
      throw err
    }
  }, [asyncFn, loadingState])

  return {
    ...loadingState,
    data,
    execute,
    setData
  }
}

/**
 * Custom hook for managing multiple loading states (useful for independent requests)
 */
export function useMultipleLoadingStates(
  keys: string[],
  options: UseLoadingStateOptions = {}
) {
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>(
    Object.fromEntries(keys.map(k => [k, false]))
  )
  const [errors, setErrors] = useState<Record<string, string | null>>(
    Object.fromEntries(keys.map(k => [k, null]))
  )

  const setLoading = useCallback((key: string, isLoading: boolean) => {
    setLoadingStates(prev => ({ ...prev, [key]: isLoading }))
  }, [])

  const setError = useCallback((key: string, error: string | null) => {
    setErrors(prev => ({ ...prev, [key]: error }))
  }, [])

  const isAnyLoading = Object.values(loadingStates).some(v => v)
  const allErrors = Object.values(errors).filter(e => e !== null)

  return {
    loadingStates,
    errors,
    setLoading,
    setError,
    isAnyLoading,
    hasErrors: allErrors.length > 0,
    allErrors
  }
}

/**
 * Custom hook for handling paginated data fetching with loading states
 */
export function usePaginatedLoading<T>(
  fetchFn: (page: number, limit: number) => Promise<T[]>,
  options: UseLoadingStateOptions & { pageSize?: number } = {}
) {
  const { pageSize = 10, ...loadingOptions } = options
  const loadingState = useLoadingState(loadingOptions)
  
  const [data, setData] = useState<T[]>([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)

  const loadPage = useCallback(async (pageNum: number, append = false) => {
    loadingState.startLoading()
    try {
      const result = await fetchFn(pageNum, pageSize)
      setData(prev => append ? [...prev, ...result] : result)
      setPage(pageNum)
      setHasMore(result.length === pageSize)
      loadingState.stopLoading()
      return result
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load data'
      loadingState.stopLoading(errorMessage)
      throw err
    }
  }, [fetchFn, pageSize, loadingState])

  const nextPage = useCallback(async () => {
    if (!hasMore) return
    await loadPage(page + 1, true)
  }, [page, hasMore, loadPage])

  const previousPage = useCallback(async () => {
    if (page <= 1) return
    await loadPage(page - 1, false)
  }, [page, loadPage])

  const reset = useCallback(async () => {
    await loadPage(1, false)
  }, [loadPage])

  return {
    ...loadingState,
    data,
    page,
    hasMore,
    loadPage,
    nextPage,
    previousPage,
    reset
  }
}
