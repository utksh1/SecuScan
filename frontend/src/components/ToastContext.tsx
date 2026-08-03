import React, { createContext, useContext, useState, useCallback, useRef, useEffect, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

type ToastType = 'success' | 'error' | 'info' | 'warning';

const TOAST_TTL_MS = 5000

interface Toast {
    id: string
    message: string
    type: ToastType
    count: number
}

interface ToastContextType {
    addToast: (message: string, type?: ToastType) => void
    removeToast: (id: string) => void
    toasts: Toast[]
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const useToast = () => {
    const context = useContext(ToastContext)
    if (!context) throw new Error('useToast must be used within ToastProvider')
    return context
}

export const ToastProvider = ({ children }: { children: ReactNode }) => {
    const [toasts, setToasts] = useState<Toast[]>([])
    const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

    const clearTimer = useCallback((id: string) => {
        const handle = timers.current[id]
        if (handle) {
            clearTimeout(handle)
            delete timers.current[id]
        }
    }, [])

    const removeToast = useCallback((id: string) => {
        clearTimer(id)
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }, [clearTimer])

    const scheduleRemoval = useCallback((id: string) => {
        clearTimer(id)
        timers.current[id] = setTimeout(() => removeToast(id), TOAST_TTL_MS)
    }, [clearTimer, removeToast])

    const addToast = useCallback((message: string, type: ToastType = 'success') => {
        setToasts((prev) => {
            // Collapse repeated identical notifications into a single entry instead of
            // stacking duplicates (e.g. a backend call that keeps failing).
            const existing = prev.find((t) => t.message === message && t.type === type)
            if (existing) {
                scheduleRemoval(existing.id)
                return prev.map((t) =>
                    t.id === existing.id ? { ...t, count: t.count + 1 } : t,
                )
            }
            const id = Math.random().toString(36).substring(2, 9)
            scheduleRemoval(id)
            return [...prev, { id, message, type, count: 1 }]
        })
    }, [scheduleRemoval])

    // Clear any pending dismissal timers on unmount.
    useEffect(() => () => {
        Object.values(timers.current).forEach(clearTimeout)
        timers.current = {}
    }, [])

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
            {children}
            <ToastContainer />
        </ToastContext.Provider>
    )
}

export function ToastContainer() {
    const { toasts, removeToast } = useToast()

    return (
        <div
            className="fixed bottom-12 right-12 z-[100] flex flex-col gap-4 pointer-events-none"
            aria-live="polite"
            aria-relevant="additions text"
        >
            <AnimatePresence>
                {toasts.map((toast) => (
                    <motion.div
                        key={toast.id}
                        role={toast.type === 'error' || toast.type === 'warning' ? 'alert' : 'status'}
                        aria-atomic="true"
                        initial={{ opacity: 0, x: 100, scale: 0.9 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                        className={`pointer-events-auto px-8 py-5 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex items-center gap-4 min-w-[320px] relative group ${
                            toast.type === 'success' ? 'bg-rag-green text-black' :
                            toast.type === 'error' ? 'bg-rag-red text-black' :
                            toast.type === 'warning' ? 'bg-rag-amber text-black' : 'bg-rag-blue text-black'
                        }`}
                    >
                        <span className="material-symbols-outlined font-black" aria-hidden="true">
                            {toast.type === 'success' ? 'check_circle' :
                             toast.type === 'error' ? 'error' :
                             toast.type === 'warning' ? 'warning' : 'info'}
                        </span>
                        <div className="flex flex-col flex-1 overflow-hidden">
                            <span className="text-[10px] font-black uppercase tracking-widest italic opacity-50 mb-0.5">
                                {toast.type.toUpperCase()}_SIGNAL
                            </span>
                            <span className="text-xs font-black uppercase tracking-tight truncate">{toast.message}</span>
                        </div>
                        {toast.count > 1 && (
                            <span
                                className="shrink-0 px-2 py-0.5 bg-black text-white text-[10px] font-black tabular-nums"
                                aria-label={`Repeated ${toast.count} times`}
                            >
                                ×{toast.count}
                            </span>
                        )}
                        <button
                            type="button"
                            className="opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity absolute top-2 right-2"
                            aria-label={`Dismiss ${toast.type} notification`}
                            onClick={() => removeToast(toast.id)}
                        >
                            <span className="material-symbols-outlined text-sm" aria-hidden="true">close</span>
                        </button>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    )
}
