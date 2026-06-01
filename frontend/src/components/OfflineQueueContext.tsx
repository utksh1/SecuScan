import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react'
import * as offlineQueue from '../services/offlineQueue'

interface OfflineQueueContextType {
  isOnline: boolean
  pendingCount: number
  queue: offlineQueue.QueuedAction[]
  enqueue: (action: Omit<offlineQueue.QueuedAction, 'id' | 'timestamp' | 'retryCount'>) => offlineQueue.QueuedAction
  retryAll: () => Promise<number>
  retry: (id: string) => Promise<boolean>
  remove: (id: string) => void
  clear: () => void
}

const OfflineQueueContext = createContext<OfflineQueueContextType | undefined>(undefined)

export function useOfflineQueue() {
  const context = useContext(OfflineQueueContext)
  if (!context) throw new Error('useOfflineQueue must be used within OfflineQueueProvider')
  return context
}

export function OfflineQueueProvider({ children }: { children: ReactNode }) {
  const [isOnline, setIsOnline] = useState(offlineQueue.isOnline())
  const [, setTick] = useState(0)

  useEffect(() => {
    const onOnline = () => {
      setIsOnline(true)
      offlineQueue.onReconnect()
    }
    const onOffline = () => setIsOnline(false)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
    return () => {
      window.removeEventListener('online', onOnline)
      window.removeEventListener('offline', onOffline)
    }
  }, [])

  useEffect(() => {
    const unsub = offlineQueue.subscribe(() => setTick((t) => t + 1))
    return unsub
  }, [])

  const enqueue = useCallback(
    (action: Omit<offlineQueue.QueuedAction, 'id' | 'timestamp' | 'retryCount'>) => {
      return offlineQueue.enqueue(action)
    },
    [],
  )

  const retryAll = useCallback(() => offlineQueue.retryAll(), [])
  const retry = useCallback((id: string) => offlineQueue.retry(id), [])
  const remove = useCallback((id: string) => offlineQueue.remove(id), [])
  const clear = useCallback(() => offlineQueue.clear(), [])

  return (
    <OfflineQueueContext.Provider
      value={{
        isOnline,
        pendingCount: offlineQueue.getQueue().length,
        queue: offlineQueue.getQueue(),
        enqueue,
        retryAll,
        retry,
        remove,
        clear,
      }}
    >
      {children}
    </OfflineQueueContext.Provider>
  )
}
