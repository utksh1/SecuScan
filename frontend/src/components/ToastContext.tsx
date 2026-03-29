import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

type ToastType = 'success' | 'error' | 'info' | 'warning';

interface Toast {
    id: string
    message: string
    type: ToastType
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

    const addToast = useCallback((message: string, type: ToastType = 'success') => {
        const id = Math.random().toString(36).substring(2, 9)
        setToasts((prev) => [...prev, { id, message, type }])
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
        }, 5000)
    }, [])

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
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
        <div className="fixed bottom-12 right-12 z-[100] flex flex-col gap-4 pointer-events-none">
            <AnimatePresence>
                {toasts.map((toast) => (
                    <motion.div
                        key={toast.id}
                        initial={{ opacity: 0, x: 100, scale: 0.9 }}
                        animate={{ opacity: 1, x: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9, transition: { duration: 0.2 } }}
                        className={`pointer-events-auto px-8 py-5 border-4 border-black shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] flex items-center gap-4 min-w-[320px] relative group cursor-pointer ${
                            toast.type === 'success' ? 'bg-rag-green text-black' :
                            toast.type === 'error' ? 'bg-rag-red text-black' :
                            toast.type === 'warning' ? 'bg-rag-amber text-black' : 'bg-rag-blue text-black'
                        }`}
                        onClick={() => removeToast(toast.id)}
                    >
                        <span className="material-symbols-outlined font-black">
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
                        <button className="opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2">
                            <span className="material-symbols-outlined text-sm">close</span>
                        </button>
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    )
}
